from crawl4ai import CrawlerRunConfig, CacheMode
from urllib.parse import urlsplit, urlunsplit
from bs4 import BeautifulSoup

import re

import config as config
import helper as helper


# ============================================================
# PARSE POSTED AGE
# ============================================================

def parse_posted_age_hours(posted_at: str) -> float | None:
    """
    Chuyển thời gian ITviec thành số giờ.

    Ví dụ:
        Posted 13 minutes ago -> 0.2167 giờ
        Posted 2 hours ago     -> 2 giờ
        Posted 1 day ago       -> 24 giờ
        Posted 2 days ago      -> 48 giờ
        Posted 1 week ago      -> 168 giờ
    """

    if not posted_at:
        return None

    text = posted_at.lower().strip()

    # --------------------------------------------------------
    # Minutes
    # --------------------------------------------------------

    match = re.search(r"(\d+)\s*minute", text)

    if match:
        minutes = int(match.group(1))
        return minutes / 60

    # --------------------------------------------------------
    # Hours
    # --------------------------------------------------------

    match = re.search(r"(\d+)\s*hour", text)

    if match:
        hours = int(match.group(1))
        return float(hours)

    # --------------------------------------------------------
    # Days
    # --------------------------------------------------------

    match = re.search(r"(\d+)\s*day", text)

    if match:
        days = int(match.group(1))
        return days * 24

    # --------------------------------------------------------
    # Weeks
    # --------------------------------------------------------

    match = re.search(r"(\d+)\s*week", text)

    if match:
        weeks = int(match.group(1))
        return weeks * 24 * 7

    return None


# ============================================================
# BUILD IT VIEC URL
# ============================================================

def build_itviec_url(keyword: str, page: int) -> str:
    """
    Tạo URL trang tìm kiếm ITviec.

    Page 1:
        /it-jobs/java

    Page 2:
        /it-jobs/java?page=2

    Page 3:
        /it-jobs/java?page=3
    """

    base_url = (
        f"{config.BASE_URL.rstrip('/')}/it-jobs/{keyword}"
    )

    if page == 1:
        return base_url

    return f"{base_url}?page={page}"


# ============================================================
# EXTRACT JOB CARDS
# ============================================================

async def extract_job_cards(
    crawler,
    url: str,
    title_keywords: list[str] | None = None,
    max_job_age_hours: int = 24,
    seen_urls: set[str] | None = None,
):
    """
    Crawl trang ITviec và parse dữ liệu từ từng job card.

    Lọc:
    - Title phải chứa ít nhất một keyword trong title_keywords.
    - Posted time phải <= max_job_age_hours.
    - Không lấy URL trùng.

    Lấy:
    - title
    - company
    - url
    - salary
    - location
    - working_model
    - posted_at
    - skills

    Các field:
    - experience
    - description
    - requirements
    - benefits

    sẽ được lấy từ trang detail.
    """

    # print("\n🌐 Crawl job list:")
    # print(url)

    # ========================================================
    # CRAWL LIST PAGE
    # ========================================================

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="domcontentloaded",
        delay_before_return_html=config.LIST_PAGE_WAIT,
    )

    result = await crawler.arun(
        url=url,
        config=run_config,
    )

    if not result.success:
        print("❌ Crawl thất bại")
        print(result.error_message)
        return []

    html = result.html

    if not html:
        print("❌ Không có HTML")
        return []

    # ========================================================
    # PARSE HTML
    # ========================================================

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # ========================================================
    # LẤY JOB CARDS
    # ========================================================

    cards = soup.select(
        'div.job-card[data-search--pagination-target="jobCard"]'
    )

    # print(f"\n📦 Tìm thấy {len(cards)} job cards")

    if not cards:
        return []

    jobs = []

    # Nếu không truyền seen_urls thì tạo mới
    if seen_urls is None:
        seen_urls = set()

    # ========================================================
    # NORMALIZE KEYWORDS
    # ========================================================

    normalized_keywords = []

    if title_keywords:
        normalized_keywords = [
            keyword.lower().strip()
            for keyword in title_keywords
            if keyword and keyword.strip()
        ]

    # ========================================================
    # PARSE TỪNG CARD
    # ========================================================

    for index, card in enumerate(cards, start=1):

        # ----------------------------------------------------
        # TITLE + URL
        # ----------------------------------------------------

        title_link = card.select_one(
            'h3[data-search--job-selection-target="jobTitle"] '
            'a[href*="/it-jobs/"]'
        )

        if not title_link:
            continue

        title = helper.clean_text(
            title_link.get_text(
                " ",
                strip=True
            )
        )

        if not title:
            continue

        # ====================================================
        # FILTER TITLE
        # ====================================================

        if normalized_keywords:

            title_lower = title.lower()

            matched_keyword = None

            for keyword in normalized_keywords:

                if keyword in title_lower:
                    matched_keyword = keyword
                    break

            if not matched_keyword:
                continue

        # ----------------------------------------------------
        # URL
        # ----------------------------------------------------

        href = title_link.get(
            "href",
            ""
        )

        if not href:
            continue

        full_url = helper.get_absolute_url(
            href
        )

        if not full_url:
            continue

        full_url = helper.normalize_url(
            full_url
        )

        if not full_url:
            continue

        # ----------------------------------------------------
        # Xóa query params và fragment
        # ----------------------------------------------------

        parsed_url = urlsplit(
            full_url
        )

        full_url = urlunsplit(
            (
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                "",
                "",
            )
        )

        # ----------------------------------------------------
        # CHỐNG DUPLICATE
        # ----------------------------------------------------

        if full_url in seen_urls:
            continue

        # ====================================================
        # COMPANY
        # ====================================================

        company = ""

        company_link = card.select_one(
            "span.ims-2 a[href*='/companies/']"
        )

        if company_link:

            company = helper.clean_text(
                company_link.get_text(
                    " ",
                    strip=True
                )
            )

        # ====================================================
        # SALARY
        # ====================================================

        salary = ""

        salary_element = card.select_one(
            "div.salary"
        )

        if salary_element:

            salary = helper.clean_text(
                salary_element.get_text(
                    " ",
                    strip=True
                )
            )

        # ====================================================
        # WORKING MODEL + LOCATION
        # ====================================================

        working_model = ""
        location = ""

        info_container = card.select_one(
            "div.imt-1.d-flex.align-items-center."
            "text-dark-grey.igap-2.small-text"
        )

        if info_container:

            # ------------------------------------------------
            # Working model
            # ------------------------------------------------

            working_model_element = (
                info_container.select_one(
                    "div.text-rich-grey.flex-shrink-0"
                )
            )

            if working_model_element:

                working_model = helper.clean_text(
                    working_model_element.get_text(
                        " ",
                        strip=True
                    )
                )

            # ------------------------------------------------
            # Location
            # ------------------------------------------------

            location_element = (
                info_container.select_one(
                    "div[title]"
                )
            )

            if location_element:

                location = helper.clean_text(
                    location_element.get_text(
                        " ",
                        strip=True
                    )
                )

                # Ưu tiên title
                title_value = (
                    location_element.get("title")
                )

                if title_value:

                    location = helper.clean_text(
                        title_value
                    )

        # ====================================================
        # POSTED AT
        # ====================================================

        posted_at = ""

        posted_element = card.select_one(
            "span.small-text.text-dark-grey"
        )

        if posted_element:

            posted_at = helper.clean_text(
                posted_element.get_text(
                    " ",
                    strip=True
                )
            )

        # ====================================================
        # FILTER POSTED TIME
        # ====================================================

        age_hours = parse_posted_age_hours(
            posted_at
        )

        if age_hours is None:

            continue

        if age_hours > max_job_age_hours:

            # print(
            #     f"⏭️ Skip job cũ: "
            #     f"{title} | "
            #     f"{posted_at} | "
            #     f"{age_hours:.1f}h"
            # )

            continue

        # ====================================================
        # SKILLS
        # ====================================================

        skills = []

        skill_elements = card.select(
            "div[data-controller='responsive-tag-list'] "
            "a[data-responsive-tag-list-target='tag']"
        )

        for skill_element in skill_elements:

            skill = helper.clean_text(
                skill_element.get_text(
                    " ",
                    strip=True
                )
            )

            if skill:
                skills.append(skill)

        # ====================================================
        # ĐÁNH DẤU URL ĐÃ THẤY
        # ====================================================

        seen_urls.add(full_url)

        # ====================================================
        # JOB OBJECT
        # ====================================================

        job = {
            "title": title,
            "company": company,
            "url": full_url,
            "salary": salary,
            "location": location,
            "working_model": working_model,
            "experience": "",
            "description": "",
            "requirements": "",
            "benefits": "",
            "posted_at": posted_at,
            "skills": skills,
        }

        jobs.append(job)

        # ====================================================
        # PRINT RESULT
        # ====================================================

        # print("\n" + "=" * 80)
        # print(f"JOB #{index}")
        # print("=" * 80)

        # print(
        #     f"Title        : {job['title']}"
        # )

        # print(
        #     f"Company      : {job['company']}"
        # )

        # print(
        #     f"URL          : {job['url']}"
        # )

        # print(
        #     f"Salary       : {job['salary']}"
        # )

        # print(
        #     f"Working model: {job['working_model']}"
        # )

        # print(
        #     f"Location     : {job['location']}"
        # )

        # print(
        #     f"Posted       : {job['posted_at']}"
        # )

        # print(
        #     f"Age          : {age_hours:.1f} hours"
        # )

        # print(
        #     f"Skills       : {job['skills']}"
        # )

    return jobs


# ============================================================
# CRAWL ALL JOBS
# ============================================================

async def crawl_jobs(
    crawler,
    keywords: list[str],
    max_jobs: int = 100,
    max_job_age_hours: int = 24,
    max_pages_per_keyword: int = 20,
):
    """
    Crawl nhiều keyword và nhiều page.

    Luồng:

        keyword
            ↓
        page=1
            ↓
        page=2
            ↓
        page=3
            ↓
          ...

    Dừng khi:

    1. Đủ max_jobs
    2. Page không còn job hợp lệ
    3. Đã đạt max_pages_per_keyword

    Ví dụ:

        keywords = [
            "java",
            "spring-boot",
            "backend"
        ]

        max_jobs = 100
        max_job_age_hours = 24
    """

    all_jobs = []

    # Dùng chung cho tất cả keyword/page
    seen_urls = set()

    # ========================================================
    # KEYWORD LOOP
    # ========================================================

    for keyword in keywords:

        if len(all_jobs) >= max_jobs:
            break

        keyword = keyword.strip()

        if not keyword:
            continue

        # print("\n\n" + "#" * 80)
        # print(f"# 🔎 KEYWORD: {keyword}")
        # print("#" * 80)

        # ====================================================
        # PAGE LOOP
        # ====================================================

        for page in range(
            1,
            max_pages_per_keyword + 1
        ):

            # ------------------------------------------------
            # ĐỦ JOB
            # ------------------------------------------------

            if len(all_jobs) >= max_jobs:
                break

            # ------------------------------------------------
            # BUILD URL
            # ------------------------------------------------

            url = build_itviec_url(
                keyword,
                page
            )

            # ------------------------------------------------
            # CRAWL PAGE
            # ------------------------------------------------

            jobs = await extract_job_cards(
                crawler=crawler,
                url=url,

                # Title phải match ít nhất
                # một keyword
                title_keywords=keywords,

                max_job_age_hours=max_job_age_hours,

                # Dùng chung giữa các page
                # và các keyword
                seen_urls=seen_urls,
            )

            # ------------------------------------------------
            # KHÔNG CÓ JOB
            # ------------------------------------------------

            if not jobs:
                break

            # ------------------------------------------------
            # CHỈ LẤY ĐỦ SỐ LƯỢNG
            # ------------------------------------------------

            remaining = (
                max_jobs - len(all_jobs)
            )

            jobs = jobs[:remaining]

            # ------------------------------------------------
            # ADD JOBS
            # ------------------------------------------------

            all_jobs.extend(
                jobs
            )
            # ------------------------------------------------
            # ĐỦ MAX JOBS
            # ------------------------------------------------

            if len(all_jobs) >= max_jobs:
                break

    return all_jobs