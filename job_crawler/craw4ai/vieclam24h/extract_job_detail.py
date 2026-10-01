from crawl4ai import CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
import config
import re
from pathlib import Path
# ============================================================
# EXTRACT JOB DETAIL - VIECLAM24H
# ============================================================

async def extract_job_detail(crawler, url: str):
    """
    Crawl trang chi tiết Vieclam24h.

    Lấy:
        - experience
        - description
        - requirements
        - benefits
        - posted_at
        - working_model
        - location
        - skills
        - job_level
        - education
        - quantity
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

        return {
            "experience": "",
            "description": "",
            "requirements": "",
            "benefits": "",
            "posted_at": "",
            "working_model": "",
            "location": "",
            "skills": [],
            "job_level": "",
            "education": "",
            "quantity": "",
        }

    html = result.html

    if not html:
        print("❌ Không có HTML")

        return {
            "experience": "",
            "description": "",
            "requirements": "",
            "benefits": "",
            "posted_at": "",
            "working_model": "",
            "location": "",
            "skills": [],
            "job_level": "",
            "education": "",
            "quantity": "",
        }

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # ========================================================
    # DEFAULT DATA
    # ========================================================

    description = ""
    requirements = ""
    benefits = ""

    posted_at = ""
    working_model = ""
    location = ""

    experience = ""
    job_level = ""
    education = ""
    quantity = ""

    skills = []

    # ========================================================
    # HELPER:
    # NORMALIZE TEXT
    # ========================================================

    def clean_text(text: str) -> str:

        if not text:
            return ""

        text = text.replace("\xa0", " ")

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

    # ========================================================
    # HELPER:
    # EXTRACT SECTION CONTENT
    # ========================================================

    def extract_section_text(container) -> str:

        if not container:
            return ""

        # -----------------------------------------------
        # Convert <br> to newline
        # -----------------------------------------------

        for br in container.find_all("br"):

            br.replace_with("\n")

        # -----------------------------------------------
        # Extract <li>
        # -----------------------------------------------

        lines = []

        for li in container.find_all("li"):

            text = clean_text(
                li.get_text(
                    " ",
                    strip=True
                )
            )

            if text:
                lines.append(
                    f"- {text}"
                )

        # -----------------------------------------------
        # Nếu có li thì dùng danh sách li
        # -----------------------------------------------

        if lines:

            return "\n".join(lines).strip()

        # -----------------------------------------------
        # Fallback: p
        # -----------------------------------------------

        paragraphs = []

        for p in container.find_all("p"):

            text = clean_text(
                p.get_text(
                    " ",
                    strip=True
                )
            )

            if text:

                # Bỏ paragraph chỉ chứa khoảng trắng
                if text.strip():
                    paragraphs.append(text)

        if paragraphs:

            return "\n".join(
                paragraphs
            ).strip()

        # -----------------------------------------------
        # Fallback cuối
        # -----------------------------------------------

        return clean_text(
            container.get_text(
                "\n",
                strip=True
            )
        )

    # ========================================================
    # HELPER:
    # NORMALIZE HEADING
    # ========================================================

    def normalize_heading(text: str) -> str:

        text = clean_text(text)

        return text.lower()

    # ========================================================
    # PARSE MAIN SECTIONS
    #
    # HTML:
    #
    # <h2>Mô tả công việc</h2>
    # <div>...</div>
    #
    # <h2>Yêu cầu công việc</h2>
    # <div>...</div>
    #
    # <h2>Quyền lợi</h2>
    # <div>...</div>
    # ========================================================

    headings = soup.find_all("h2")

    for heading in headings:

        heading_text = normalize_heading(
            heading.get_text(
                " ",
                strip=True
            )
        )

        # -----------------------------------------------
        # Tìm div nội dung gần nhất sau h2
        # -----------------------------------------------

        content = heading.find_next_sibling()

        if not content:
            continue

        # ==================================================
        # MÔ TẢ CÔNG VIỆC
        # ==================================================

        if (
            "mô tả công việc" in heading_text
            or "mô tả" in heading_text
            or "job description" in heading_text
        ):

            description = extract_section_text(
                content
            )

        # ==================================================
        # YÊU CẦU CÔNG VIỆC
        # ==================================================

        elif (
            "yêu cầu công việc" in heading_text
            or "yêu cầu" in heading_text
            or "requirements" in heading_text
        ):

            requirements = extract_section_text(
                content
            )

        # ==================================================
        # QUYỀN LỢI
        # ==================================================

        elif (
            "quyền lợi" in heading_text
        ):
            benefits = extract_section_text(
                content
            )

        # ==================================================
        # KỸ NĂNG CẦN THIẾT
        # ==================================================

        elif (
            "kỹ năng cần thiết" in heading_text
            or "kỹ năng" in heading_text
            or "skills" in heading_text
        ):

            skill_container = content

            skill_divs = skill_container.select(
                "div"
            )

            for div in skill_divs:

                classes = div.get("class", [])

                # Chỉ lấy div text nhỏ,
                # tránh lấy cả container lớn
                if "text-14" not in classes:
                    continue

                text = clean_text(
                    div.get_text(
                        " ",
                        strip=True
                    )
                )

                if not text:
                    continue

                # Không lấy dấu phân cách
                if text == "•":
                    continue

                if text not in skills:

                    skills.append(text)

    # ========================================================
    # PARSE "THÔNG TIN CHUNG"
    # ========================================================

    # Tìm heading Thông tin chung
    general_heading = None

    for heading in headings:

        heading_text = normalize_heading(
            heading.get_text(
                " ",
                strip=True
            )
        )

        if "thông tin chung" in heading_text:

            general_heading = heading

            break

    if general_heading:

        # Lấy container lớn sau heading
        general_container = general_heading.find_next_sibling()

        if general_container:

            # ---------------------------------------------
            # Các block:
            #
            # Ngày đăng -> 07/09/2026
            # Cấp bậc -> Nhân viên
            # Số lượng tuyển -> 4
            # Hình thức làm việc -> Toàn thời gian cố định
            # Yêu cầu bằng cấp -> Cao đẳng
            # Yêu cầu kinh nghiệm -> Dưới 1 năm
            # ---------------------------------------------

            labels = general_container.find_all(
                string=True
            )

            for label_node in labels:

                label = clean_text(
                    str(label_node)
                )

                if not label:
                    continue

                # =========================================
                # NGÀY ĐĂNG
                # =========================================

                if label == "Ngày đăng":

                    parent = label_node.parent

                    if parent:

                        value_element = parent.find_next_sibling()

                        if value_element:

                            posted_at = clean_text(
                                value_element.get_text(
                                    " ",
                                    strip=True
                                )
                            )

                # =========================================
                # CẤP BẬC
                # =========================================

                elif label == "Cấp bậc":

                    parent = label_node.parent

                    if parent:

                        value_element = parent.find_next_sibling()

                        if value_element:

                            job_level = clean_text(
                                value_element.get_text(
                                    " ",
                                    strip=True
                                )
                            )

                # =========================================
                # SỐ LƯỢNG TUYỂN
                # =========================================

                elif label == "Số lượng tuyển":

                    parent = label_node.parent

                    if parent:

                        value_element = parent.find_next_sibling()

                        if value_element:

                            quantity = clean_text(
                                value_element.get_text(
                                    " ",
                                    strip=True
                                )
                            )

                # =========================================
                # HÌNH THỨC LÀM VIỆC
                # =========================================

                elif label == "Hình thức làm việc":

                    parent = label_node.parent

                    if parent:

                        value_element = parent.find_next_sibling()

                        if value_element:

                            working_model = clean_text(
                                value_element.get_text(
                                    " ",
                                    strip=True
                                )
                            )

                # =========================================
                # YÊU CẦU BẰNG CẤP
                # =========================================

                elif label == "Yêu cầu bằng cấp":

                    parent = label_node.parent

                    if parent:

                        value_element = parent.find_next_sibling()

                        if value_element:

                            education = clean_text(
                                value_element.get_text(
                                    " ",
                                    strip=True
                                )
                            )

                # =========================================
                # YÊU CẦU KINH NGHIỆM
                # =========================================

                elif label == "Yêu cầu kinh nghiệm":

                    parent = label_node.parent

                    if parent:

                        value_element = parent.find_next_sibling()

                        if value_element:

                            experience = clean_text(
                                value_element.get_text(
                                    " ",
                                    strip=True
                                )
                            )

    # ========================================================
    # PARSE EXPERIENCE FALLBACK
    #
    # Nếu không lấy được từ "Thông tin chung"
    # thì thử tìm trong requirements.
    # ========================================================

    if not experience:

        experience = extract_experience(
            requirements
        )

    # ========================================================
    # PARSE LOCATION
    #
    # HTML:
    #
    # <h2>Địa điểm làm việc</h2>
    #
    # TP.HCM: KDC Park Riverside...
    # Hà Nội: Khách sạn thể thao...
    # ========================================================

    location_parts = []

    for heading in headings:

        heading_text = normalize_heading(
            heading.get_text(
                " ",
                strip=True
            )
        )

        if "địa điểm làm việc" not in heading_text:
            continue

        location_container = heading.find_next_sibling()

        if not location_container:
            continue

        # Tìm các icon location
        location_rows = location_container.select(
            "div.flex.items-center.gap-1"
        )

        for row in location_rows:

            text = clean_text(
                row.get_text(
                    " ",
                    strip=True
                )
            )

            if text and text not in location_parts:

                location_parts.append(text)

    if location_parts:

        location = " | ".join(
            location_parts
        )

    # ========================================================
    # RETURN
    # ========================================================

    detail = {
        "experience": experience,

        "description": description,

        "requirements": requirements,

        "benefits": benefits,

        "posted_at": posted_at,

        "working_model": working_model,

        "location": location,

        "skills": skills,

        "job_level": job_level,

        "education": education,

        "quantity": quantity,
    }

    return detail


# ============================================================
# EXTRACT EXPERIENCE FROM REQUIREMENTS
# ============================================================

def extract_experience(requirements: str) -> str:
    """
    Fallback lấy kinh nghiệm từ requirements.

    Ví dụ:
        1 năm
        2 năm
        2+ năm
        1-2 năm
        2 years
        2+ years
        Dưới 1 năm
        Không yêu cầu kinh nghiệm
    """

    if not requirements:
        return ""

    lines = requirements.split("\n")

    experience_lines = []

    patterns = [
        r"\b\d+\s*[-–]\s*\d+\s*(?:năm|years?)\b",
        r"\b\d+\s*\+?\s*(?:năm|years?)\b",
        r"\b(?:dưới|trên|ít nhất|tối thiểu)\s+\d+\s*(?:năm|years?)\b",
        r"\bkhông\s+(?:yêu cầu|cần)\s+(?:kinh nghiệm|experience)\b",
    ]

    compiled_patterns = [
        re.compile(
            pattern,
            re.IGNORECASE
        )
        for pattern in patterns
    ]

    for line in lines:

        line = line.strip()

        if not line:
            continue

        for pattern in compiled_patterns:

            if pattern.search(line):

                experience_lines.append(
                    line
                )

                break

    return "\n".join(
        experience_lines
    )
