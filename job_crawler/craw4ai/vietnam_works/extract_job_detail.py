from crawl4ai import CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
import config
import helper
import re


EMPTY_DETAIL = {
    "experience": "",
    "description": "",
    "requirements": "",
    "benefits": "",
}


async def extract_job_detail(crawler, url: str):
    """
    Crawl trang chi tiết VietnamWorks và lấy:

    - description
    - requirements
    - benefits
    - experience
    """

    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="domcontentloaded",
        delay_before_return_html=config.DETAIL_PAGE_WAIT,
        magic=True,
    )

    result = await crawler.arun(
        url=url,
        config=run_config,
    )

    if not result.success:
        print("❌ Crawl detail thất bại")
        print(result.error_message)
        return EMPTY_DETAIL.copy()

    html = result.html

    if not html:
        print("❌ Không có HTML")
        return EMPTY_DETAIL.copy()

    soup = BeautifulSoup(html, "html.parser")

    description = ""
    requirements = ""
    benefits = ""
    experience = ""

    # =========================================================
    # Tìm tất cả heading của các section
    # VietnamWorks hiện dùng h2 cho các section
    # =========================================================

    headings = soup.find_all(["h2", "h3"])

    for heading in headings:

        title = helper.clean_text(
            heading.get_text(" ", strip=True)
        )

        if not title:
            continue

        title_lower = normalize_text(title)

        # -----------------------------------------------------
        # Lấy container nội dung phía sau heading
        # -----------------------------------------------------

        content = get_section_content(heading)

        if not content:
            continue

        section_text = extract_section_text(content)

        if not section_text:
            continue

        # =====================================================
        # DESCRIPTION
        # =====================================================

        if is_description_section(title_lower):

            if not description:
                description = section_text

        # =====================================================
        # REQUIREMENTS
        # =====================================================

        elif is_requirement_section(title_lower):

            if not requirements:
                requirements = section_text

            # Tách experience từ requirements
            detected_experience = extract_experience(
                section_text
            )

            if detected_experience:
                experience = detected_experience

        # =====================================================
        # BENEFITS
        # =====================================================

        elif is_benefit_section(title_lower):

            if not benefits:
                benefits = section_text

        # =====================================================
        # EXPERIENCE
        # =====================================================

        elif is_experience_section(title_lower):

            experience = section_text

    # =========================================================
    # Nếu experience chưa tìm thấy trong requirements
    # thì thử tìm trong toàn bộ text của trang
    # =========================================================

    if not experience:

        page_text = helper.clean_text(
            soup.get_text("\n", strip=True)
        )

        experience = extract_experience(page_text)

    # =========================================================
    # Kết quả
    # =========================================================

    result_data = {
        "experience": experience,
        "description": description,
        "requirements": requirements,
        "benefits": benefits,
    }

    return result_data


# =============================================================
# NORMALIZE TEXT
# =============================================================

def normalize_text(text: str) -> str:
    """
    Chuẩn hóa text để dễ kiểm tra section.

    Ví dụ:
        "Mô tả công việc"
        -> "mo ta cong viec"
    """

    if not text:
        return ""

    text = text.lower().strip()

    # bỏ dấu tiếng Việt
    replacements = {
        "á": "a",
        "à": "a",
        "ả": "a",
        "ã": "a",
        "ạ": "a",

        "ă": "a",
        "ắ": "a",
        "ằ": "a",
        "ẳ": "a",
        "ẵ": "a",
        "ặ": "a",

        "â": "a",
        "ấ": "a",
        "ầ": "a",
        "ẩ": "a",
        "ẫ": "a",
        "ậ": "a",

        "é": "e",
        "è": "e",
        "ẻ": "e",
        "ẽ": "e",
        "ẹ": "e",

        "ê": "e",
        "ế": "e",
        "ề": "e",
        "ể": "e",
        "ễ": "e",
        "ệ": "e",

        "í": "i",
        "ì": "i",
        "ỉ": "i",
        "ĩ": "i",
        "ị": "i",

        "ó": "o",
        "ò": "o",
        "ỏ": "o",
        "õ": "o",
        "ọ": "o",

        "ô": "o",
        "ố": "o",
        "ồ": "o",
        "ổ": "o",
        "ỗ": "o",
        "ộ": "o",

        "ơ": "o",
        "ớ": "o",
        "ờ": "o",
        "ở": "o",
        "ỡ": "o",
        "ợ": "o",

        "ú": "u",
        "ù": "u",
        "ủ": "u",
        "ũ": "u",
        "ụ": "u",

        "ư": "u",
        "ứ": "u",
        "ừ": "u",
        "ử": "u",
        "ữ": "u",
        "ự": "u",

        "ý": "y",
        "ỳ": "y",
        "ỷ": "y",
        "ỹ": "y",
        "ỵ": "y",

        "đ": "d",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


# =============================================================
# TÌM CONTENT CỦA SECTION
# =============================================================

def get_section_content(heading):
    """
    Với HTML:

    <h2>Mô tả công việc</h2>
    <div>
        <p>...</p>
        <p>...</p>
    </div>

    sẽ lấy div phía sau h2.

    Không phụ thuộc class sc-xxxx dynamic.
    """

    # Cách 1:
    # lấy sibling kế tiếp có nội dung
    sibling = heading.find_next_sibling()

    if sibling:
        return sibling

    # Cách 2:
    # nếu HTML có wrapper phức tạp
    parent = heading.parent

    if parent:
        for child in parent.children:

            if child == heading:
                continue

            if getattr(child, "name", None):
                return child

    return None


# =============================================================
# EXTRACT SECTION TEXT
# =============================================================

def extract_section_text(section) -> str:

    if not section:
        return ""

    # Clone HTML để không ảnh hưởng soup gốc
    section = BeautifulSoup(
        str(section),
        "html.parser",
    )

    # ---------------------------------------------------------
    # Xử lý <br>
    # ---------------------------------------------------------

    for br in section.find_all("br"):
        br.replace_with("\n")

    # ---------------------------------------------------------
    # Xử lý <li>
    # ---------------------------------------------------------

    for li in section.find_all("li"):

        text = li.get_text(
            " ",
            strip=True,
        )

        if text:
            li.replace_with(
                f"\n- {text}\n"
            )

    # ---------------------------------------------------------
    # Xử lý paragraph
    # ---------------------------------------------------------

    for p in section.find_all("p"):

        text = p.get_text(
            " ",
            strip=True,
        )

        if text:
            p.replace_with(
                f"\n{text}\n"
            )

    # ---------------------------------------------------------
    # Lấy text
    # ---------------------------------------------------------

    text = section.get_text(
        "\n",
        strip=True,
    )

    # ---------------------------------------------------------
    # Normalize whitespace
    # ---------------------------------------------------------

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    # Nhiều newline -> 1 newline
    text = re.sub(
        r"\n\s*\n+",
        "\n",
        text,
    )

    # ---------------------------------------------------------
    # Remove duplicate blank lines
    # ---------------------------------------------------------

    lines = []

    for line in text.splitlines():

        line = line.strip()

        if line:
            lines.append(line)

    return "\n".join(lines).strip()


# =============================================================
# SECTION DETECTION
# =============================================================

def is_description_section(title: str) -> bool:

    keywords = [
        "mo ta",
        "mo ta cong viec",
        "job description",
        "description",
        "cong viec",
        "responsibilities",
        "trach nhiem",
    ]

    return any(
        keyword in title
        for keyword in keywords
    )


def is_requirement_section(title: str) -> bool:

    keywords = [
        "yeu cau",
        "yeu cau cong viec",
        "requirements",
        "requirement",
        "qualification",
        "qualifications",
        "ky nang",
        "kien thuc",
        "skills",
        "your skills",
    ]

    return any(
        keyword in title
        for keyword in keywords
    )


def is_benefit_section(title: str) -> bool:

    keywords = [
        "quyen loi",
        "phuc loi",
        "benefits",
        "benefit",
        "why you'll love",
        "why you will love",
        "che do",
    ]

    return any(
        keyword in title
        for keyword in keywords
    )


def is_experience_section(title: str) -> bool:

    keywords = [
        "kinh nghiem",
        "experience",
        "work experience",
        "years of experience",
    ]

    return any(
        keyword in title
        for keyword in keywords
    )


# =============================================================
# EXTRACT EXPERIENCE
# =============================================================

def extract_experience(text: str) -> str:

    if not text:
        return ""

    experience_lines = []

    # ---------------------------------------------------------
    # Các dạng:
    #
    # 2 years
    # 2+ years
    # 2 năm
    # 2+ năm
    # 1 - 2 years
    # 1-2 năm
    # ---------------------------------------------------------

    patterns = [
        re.compile(
            r"\b\d+\s*\+?\s*(years?|năm)\b",
            re.IGNORECASE,
        ),

        re.compile(
            r"\b\d+\s*[-–]\s*\d+\s*(years?|năm)\b",
            re.IGNORECASE,
        ),

        re.compile(
            r"\b(?:at least|minimum|tối thiểu)"
            r".{0,30}"
            r"\d+\s*\+?\s*(years?|năm)",
            re.IGNORECASE,
        ),
    ]

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        for pattern in patterns:

            if pattern.search(line):

                if line not in experience_lines:
                    experience_lines.append(line)

                break

    return "\n".join(experience_lines)