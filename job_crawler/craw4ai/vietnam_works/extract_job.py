from crawl4ai import CrawlerRunConfig, CacheMode
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from bs4 import BeautifulSoup
import re

import config
import helper


# ============================================================
# PARSE POSTED AGE
# ============================================================

def parse_posted_age_hours(posted_at: str) -> float | None:
    """
    Parse các dạng:
        Mới
        Cập nhật hôm nay
        Đăng hôm nay
        Đăng 4 giờ trước
        Đăng 30 phút trước
        Đăng 2 ngày trước
    """

    if not posted_at:
        return None

    text = posted_at.lower().strip()

    # --------------------------------------------------------
    # Minutes
    # --------------------------------------------------------
    match = re.search(
        r"(\d+)\s*(phút|minute|minutes)",
        text
    )
    if match:
        return int(match.group(1)) / 60

    # --------------------------------------------------------
    # Hours
    # --------------------------------------------------------
    match = re.search(
        r"(\d+)\s*(giờ|hour|hours)",
        text
    )
    if match:
        return float(match.group(1))

    # --------------------------------------------------------
    # Days
    # --------------------------------------------------------
    match = re.search(
        r"(\d+)\s*(ngày|day|days)",
        text
    )
    if match:
        return int(match.group(1)) * 24

    # --------------------------------------------------------
    # Weeks
    # --------------------------------------------------------
    match = re.search(
        r"(\d+)\s*(tuần|week|weeks)",
        text
    )
    if match:
        return int(match.group(1)) * 24 * 7

    # --------------------------------------------------------
    # Months
    # --------------------------------------------------------
    match = re.search(
        r"(\d+)\s*(tháng|month|months)",
        text
    )
    if match:
        return int(match.group(1)) * 24 * 30

    # --------------------------------------------------------
    # "Hôm nay"
    # --------------------------------------------------------
    if "hôm nay" in text or "today" in text:
        return 0

    # --------------------------------------------------------
    # "Mới"
    # --------------------------------------------------------
    if text == "mới" or " mới" in text:
        return 0

    return None


# ============================================================
# BUILD VIETNAMWORKS URL
# ============================================================

def parse_vietnamworks_posted_age_hours(posted_at: str) -> float | None:
    text = (posted_at or "").lower().strip()
    patterns = (
        (r"(\d+)\s*(?:ph\u00fat|minute|minutes)", 1 / 60),
        (r"(\d+)\s*(?:gi\u1edd|hour|hours)", 1),
        (r"(\d+)\s*(?:ng\u00e0y|day|days)", 24),
        (r"(\d+)\s*(?:tu\u1ea7n|week|weeks)", 24 * 7),
        (r"(\d+)\s*(?:th\u00e1ng|month|months)", 24 * 30),
    )
    for pattern, multiplier in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1)) * multiplier
    if any(token in text for token in ("h\u00f4m nay", "today", "m\u1edbi", "just posted")):
        return 0
    return None

def build_vietnamworks_url(page: int) -> str:
    """
    Tạo URL search VietnamWorks.

    Nên cấu hình SEARCH_URL trong config.py.

    Ví dụ:

        BASE_URL = "https://www.vietnamworks.com"
        SEARCH_URL = "/tim-viec-lam"

    URL tạo ra:

        https://www.vietnamworks.com/tim-viec-lam?keyword=java
        https://www.vietnamworks.com/tim-viec-lam?keyword=java&page=2
    """

    parsed = urlsplit(config.START_URL)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.pop("keyword", None)
    if page > 1:
        params["page"] = str(page)
    else:
        params.pop("page", None)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(params), ""))


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
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="domcontentloaded",
        delay_before_return_html=config.LIST_PAGE_WAIT,
        magic=True,
    )

    result = await crawler.arun(
        url=url,
        config=run_config
    )

    # ========================================================
    # CRAWL ERROR
    # ========================================================

    if not result.success:
        print(
            "❌ Crawl thất bại:",
            result.error_message
        )
        return []

    html = result.html

    if not html:
        print("❌ Không có HTML")
        return []

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # ========================================================
    # FIND JOB CARDS
    # ========================================================

    cards = soup.select(
        "div.search_list.view_job_item"
    )

    if not cards:
        return []

    # ========================================================
    # INIT
    # ========================================================

    jobs = []

    if seen_urls is None:
        seen_urls = set()

    normalized_keywords = []

    if title_keywords:
        normalized_keywords = [
            k.lower().strip()
            for k in title_keywords
            if k and k.strip()
        ]

    # ========================================================
    # LOOP CARDS
    # ========================================================

    for index, card in enumerate(
        cards,
        start=1
    ):

        # ====================================================
        # TITLE + URL
        # ====================================================

        title_link = card.select_one(
            "h2 a[href]"
        )

        if not title_link:
            continue

        title = helper.clean_text(
            title_link.get_text(
                " ",
                strip=True
            )
        )

        # Remove "Mới" nếu nằm trong title
        title = re.sub(
            r"^Mới\s+",
            "",
            title,
            flags=re.IGNORECASE
        ).strip()

        if not title:
            continue

        # ====================================================
        # TITLE KEYWORD FILTER
        # ====================================================

        if normalized_keywords:

            title_lower = title.lower()

            if not any(
                keyword in title_lower
                for keyword in normalized_keywords
            ):
                continue

        # ====================================================
        # URL
        # ====================================================

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

        # Remove query string
        parsed_url = urlsplit(
            full_url
        )

        full_url = urlunsplit(
            (
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                "",
                ""
            )
        )

        # ====================================================
        # DUPLICATE
        # ====================================================

        if full_url in seen_urls:
            continue

        # ====================================================
        # COMPANY
        # ====================================================

        company = ""

        company_link = card.select_one(
            'a[href*="/nha-tuyen-dung/"]'
        )

        if company_link:
            company = helper.clean_text(
                company_link.get_text(
                    " ",
                    strip=True
                )
            )

        # ====================================================
        # SALARY + LOCATION
        # ====================================================

        salary = ""
        location = ""

        # Block:
        #
        # <div ...>
        #     <span>$ 400-1,500 /tháng</span>
        #     <div></div>
        #     <span>Hồ Chí Minh</span>
        # </div>

        info_block = card.select_one(
            "div.dvwCOM"
        )

        if info_block:

            spans = info_block.select(
                ":scope > span"
            )

            if len(spans) >= 1:
                salary = helper.clean_text(
                    spans[0].get_text(
                        " ",
                        strip=True
                    )
                )

            if len(spans) >= 2:
                location = helper.clean_text(
                    spans[-1].get_text(
                        " ",
                        strip=True
                    )
                )

        # Fallback salary
        if not salary:

            salary_element = card.select_one(
                'span[class*="salary"]'
            )

            if salary_element:
                salary = helper.clean_text(
                    salary_element.get_text(
                        " ",
                        strip=True
                    )
                )

        # Fallback location
        if not location:

            location_element = card.select_one(
                'span[class*="city"]'
            )

            if location_element:
                location = helper.clean_text(
                    location_element.get_text(
                        " ",
                        strip=True
                    )
                )

        # ====================================================
        # POSTED AT
        # ====================================================

        posted_at = ""

        signal_block = card.select_one(
            "div[data-applicant-signal-value]"
        )

        if signal_block:

            # Lấy tất cả text nhưng loại bỏ icon/SVG
            for svg in signal_block.select("svg"):
                svg.decompose()

            posted_at = helper.clean_text(
                signal_block.get_text(
                    " ",
                    strip=True
                )
            )

        # Ví dụ:
        #
        # "Cập nhật hôm nay | Hãy là ứng viên đầu tiên"
        #
        # "Đăng 4 giờ trước | Hãy là 1 trong 5 ứng viên đầu tiên"
        #
        # Chỉ lấy phần đầu tiên.

        if "|" in posted_at:
            posted_at = posted_at.split(
                "|",
                1
            )[0].strip()

        # ====================================================
        # AGE FILTER
        # ====================================================

        age_hours = parse_vietnamworks_posted_age_hours(
            posted_at
        )

        if age_hours is None:

            # Không nên tự động cho = 0
            # vì sẽ làm job cũ lọt vào filter.
            continue

        if age_hours > max_job_age_hours:

            continue

        # ====================================================
        # SKILLS
        # ====================================================

        skills = []

        # HTML:
        #
        # <label title="Customer Management">
        # <label title="Marketing Support">
        # <label title="Chăm Sóc Khách Hàng">

        skill_elements = card.select(
            'label[title]'
        )

        for skill_element in skill_elements:

            skill = (
                skill_element.get(
                    "title",
                    ""
                ).strip()
            )

            if skill:
                skills.append(skill)

        # Remove duplicate skills
        skills = list(
            dict.fromkeys(skills)
        )

        # ====================================================
        # ADD SEEN URL
        # ====================================================

        seen_urls.add(
            full_url
        )

        # ====================================================
        # CREATE JOB
        # ====================================================

        job = {
            "title": title,
            "company": company,
            "url": full_url,
            "salary": salary,
            "location": location,
            "working_model": "",
            "experience": "",
            "description": "",
            "requirements": "",
            "benefits": "",
            "posted_at": posted_at,
            "skills": skills,
        }

        jobs.append(job)

    return jobs


# ============================================================
# CRAWL JOBS
# ============================================================

async def crawl_jobs(
    crawler,
    keywords: list[str],
    max_jobs: int = 100,
    max_job_age_hours: int = 24,
    max_pages_per_keyword: int = 20,
):

    all_jobs = []

    seen_urls = set()

    # ========================================================
    # LOOP KEYWORDS
    # ========================================================

    for keyword in [", ".join(keywords)]:

        if len(all_jobs) >= max_jobs:
            break

        keyword = keyword.strip()

        if not keyword:
            continue

        # ====================================================
        # LOOP PAGES
        # ====================================================

        for page in range(
            1,
            max_pages_per_keyword + 1
        ):

            if len(all_jobs) >= max_jobs:
                break

            url = build_vietnamworks_url(page=page)

            jobs = await extract_job_cards(
                crawler=crawler,
                url=url,

                # Quan trọng:
                # Chỉ filter theo keyword hiện tại
                title_keywords=keywords,

                max_job_age_hours=max_job_age_hours,

                seen_urls=seen_urls,
            )

            # =================================================
            # NO JOB
            # =================================================

            if not jobs:

                continue

            # =================================================
            # ADD JOBS
            # =================================================

            remaining = (
                max_jobs
                - len(all_jobs)
            )

            all_jobs.extend(
                jobs[:remaining]
            )

            # =================================================
            # TARGET REACHED
            # =================================================

            if len(all_jobs) >= max_jobs:

                break

    return all_jobs
