from crawl4ai import CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup

import config as config
import helper as helper
import re


# ============================================================
# EXTRACT JOB DETAIL
# ============================================================

async def extract_job_detail(crawler, url: str):
    """
    Crawl trang detail ITviec và lấy:

    - description
    - requirements
    - benefits
    - experience

    HTML chính:

        <section class="job-content ...">
            <div class="paragraph">
                <h2>Job description</h2>
                ...
            </div>

            <div class="paragraph">
                <h2>Your skills and experience</h2>
                ...
            </div>

            <div class="paragraph">
                <h2>Why you'll love working here</h2>
                ...
            </div>
        </section>
    """



    # ========================================================
    # CRAWL DETAIL PAGE
    # ========================================================

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="domcontentloaded",
        delay_before_return_html=config.DETAIL_PAGE_WAIT,
    )

    result = await crawler.arun(
        url=url,
        config=run_config,
    )

    if not result.success:
        print("❌ Crawl detail thất bại")
        print(result.error_message)
        return {
            "experience": "",
            "description": "",
            "requirements": "",
            "benefits": "",
        }

    html = result.html

    if not html:
        print("❌ Không có HTML")
        return {
            "experience": "",
            "description": "",
            "requirements": "",
            "benefits": "",
        }

    # ========================================================
    # PARSE HTML
    # ========================================================

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # ========================================================
    # JOB CONTENT
    # ========================================================

    job_content = soup.select_one(
        "section.job-content[data-jobs--jd-scroll-target='jobContent']"
    )

    if not job_content:

        print("❌ Không tìm thấy job-content")

        return {
            "experience": "",
            "description": "",
            "requirements": "",
            "benefits": "",
        }

    # ========================================================
    # DEFAULT RESULT
    # ========================================================

    description = ""
    requirements = ""
    benefits = ""
    experience = ""

    # ========================================================
    # FIND ALL SECTIONS
    # ========================================================

    sections = job_content.select(
        "div.paragraph"
    )



    # ========================================================
    # PARSE EACH SECTION
    # ========================================================

    for section in sections:

        h2 = section.select_one("h2")

        if not h2:
            continue

        section_title = helper.clean_text(
            h2.get_text(
                " ",
                strip=True
            )
        )

        section_title_lower = (
            section_title.lower()
        )



        # ====================================================
        # JOB DESCRIPTION
        # ====================================================

        if section_title_lower == "job description":

            description = extract_section_text(
                section
            )

        # ====================================================
        # SKILLS / EXPERIENCE
        # ====================================================

        elif (
            section_title_lower
            == "your skills and experience"
        ):

            requirements = extract_section_text(
                section
            )

            # -----------------------------------------------
            # Extract years of experience
            # -----------------------------------------------

            experience = extract_experience(
                requirements
            )

        # ====================================================
        # BENEFITS
        # ====================================================

        elif (
            section_title_lower
            == "why you'll love working here"
        ):

            benefits = extract_section_text(
                section
            )

    # ========================================================
    # RESULT
    # ========================================================

    result_data = {
        "experience": experience,
        "description": description,
        "requirements": requirements,
        "benefits": benefits,
    }



    return result_data


# ============================================================
# EXTRACT SECTION TEXT
# ============================================================

def extract_section_text(section):
    """
    Lấy toàn bộ nội dung trong một section.

    Giữ cấu trúc:
    - paragraph
    - ordered list
    - unordered list

    Nhưng chuyển thành plain text dễ lưu PostgreSQL
    và đưa vào AI.
    """

    # --------------------------------------------------------
    # Copy section để không làm thay đổi soup gốc
    # --------------------------------------------------------

    section = BeautifulSoup(
        str(section),
        "html.parser"
    )

    # --------------------------------------------------------
    # Xóa h2 vì title đã được xử lý bên ngoài
    # --------------------------------------------------------

    h2 = section.find("h2")

    if h2:
        h2.decompose()

    # --------------------------------------------------------
    # Xử lý <br>
    # --------------------------------------------------------

    for br in section.find_all("br"):
        br.replace_with("\n")

    # --------------------------------------------------------
    # Xử lý <li>
    # --------------------------------------------------------

    for li in section.find_all("li"):

        text = li.get_text(
            " ",
            strip=True
        )

        if text:
            li.replace_with(
                f"- {text}\n"
            )

    # --------------------------------------------------------
    # Xử lý paragraph
    # --------------------------------------------------------

    for p in section.find_all("p"):

        text = p.get_text(
            " ",
            strip=True
        )

        if text:
            p.replace_with(
                f"{text}\n"
            )

    # --------------------------------------------------------
    # Lấy text
    # --------------------------------------------------------

    text = section.get_text(
        " ",
        strip=True
    )

    # --------------------------------------------------------
    # Normalize whitespace
    # --------------------------------------------------------

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n\s*\n+",
        "\n",
        text
    )

    return text.strip()


# ============================================================
# EXTRACT EXPERIENCE
# ============================================================

def extract_experience(requirements: str) -> str:
    """
    Tìm thông tin số năm kinh nghiệm từ requirements.

    Ví dụ:

        5+ years in Backend Development

    sẽ trả:

        5+ years in Backend Development

    Nếu không tìm thấy:
        ""
    """

    if not requirements:
        return ""

    lines = requirements.split("\n")

    experience_lines = []

    # Pattern:
    # 5+ years
    # 3 years
    # 2+ years in...
    pattern = re.compile(
        r"\b\d+\+?\s+years?\b",
        re.IGNORECASE
    )

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if pattern.search(line):

            experience_lines.append(
                line
            )

    return "\n".join(
        experience_lines
    )