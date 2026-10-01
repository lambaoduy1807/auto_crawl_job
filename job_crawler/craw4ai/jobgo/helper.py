import config as config
import re
from urllib.parse import urljoin
# ============================================================
# HELPER
# ============================================================

def clean_text(text: str | None) -> str:
    """
    Làm sạch text:
    - Xóa khoảng trắng thừa
    - Xóa dòng trống
    """
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_multiline_text(text: str | None) -> str:
    """
    Giữ xuống dòng nhưng loại bỏ dòng trống.
    Phù hợp với description / requirements / benefits.
    """
    if not text:
        return ""

    lines = []

    for line in text.splitlines():
        line = clean_text(line)

        if line:
            lines.append(line)

    return "\n".join(lines)


def get_absolute_url(url: str | None) -> str:
    """
    Chuyển relative URL thành absolute URL.
    """
    if not url:
        return ""

    return urljoin(config.BASE_URL, url)


def normalize_url(url: str) -> str:
    """
    Chuẩn hóa URL.
    """
    if not url:
        return ""

    return url.split("?")[0].rstrip("/")


def extract_date(text: str | None) -> str:
    """
    Cố gắng lấy thông tin ngày đăng.
    Nếu không xác định được thì trả về text gốc.
    """
    if not text:
        return ""

    return clean_text(text)