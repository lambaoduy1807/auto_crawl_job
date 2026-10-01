"""Extract description sections from a JobsGO job detail page."""

import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup
from crawl4ai import CacheMode, CrawlerRunConfig

import config
import helper


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").casefold())
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


def _section_text(heading) -> str:
    content = heading.find_next_sibling()
    if not content:
        return ""

    list_items = [
        helper.clean_text(item.get_text(" ", strip=True))
        for item in content.select("li")
    ]
    list_items = [item for item in list_items if item]
    if list_items:
        return "\n".join(f"- {item}" for item in list_items)

    paragraphs = [
        helper.clean_text(paragraph.get_text(" ", strip=True))
        for paragraph in content.select("p")
    ]
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    if paragraphs:
        return "\n".join(paragraphs)

    return helper.clean_multiline_text(content.get_text("\n", strip=True))


def _is_access_block_page(soup: BeautifulSoup) -> bool:
    title = _normalize(soup.title.get_text(" ", strip=True)) if soup.title else ""
    body_text = _normalize(soup.get_text(" ", strip=True))
    return (
        "attention required" in title
        or "cloudflare" in title
        or soup.select_one("#cf-error-details, .cf-error-details-wrapper") is not None
        or "you are unable to access jobsgo.vn" in body_text
    )


async def extract_job_detail(crawler, url: str) -> dict | None:
    empty = {
        "experience": "",
        "description": "",
        "requirements": "",
        "benefits": "",
        "working_model": "",
        "location": "",
        "skills": [],
    }
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="domcontentloaded",
        delay_before_return_html=config.DETAIL_PAGE_WAIT,
        magic=True,
    )
    result = await crawler.arun(url=url, config=run_config)
    if not result.success or not result.html:
        print(f"JobsGO detail crawl failed: {result.error_message}")
        return None

    soup = BeautifulSoup(result.html, "html.parser")
    if _is_access_block_page(soup):
        print(
            "JobsGO detail page is a Cloudflare access-block page; "
            "no job detail fields can be extracted."
        )
        return None

    fields = {"description": "", "requirements": "", "benefits": ""}
    skills = []
    detail_card = soup.select_one(".job-detail-card") or soup
    headings = detail_card.select("h3.section-title") or detail_card.find_all(
        re.compile(r"^h[1-6]$", re.I)
    )
    for heading in headings:
        label = _normalize(helper.clean_text(heading.get_text(" ", strip=True)))
        text = _section_text(heading)
        if not text:
            continue
        if any(key in label for key in ("mo ta cong viec", "mo ta", "job description")):
            if not fields["description"]:
                fields["description"] = text
        elif any(key in label for key in ("yeu cau cong viec", "yeu cau", "requirements", "qualification")):
            if not fields["requirements"]:
                fields["requirements"] = text
        elif any(key in label for key in ("quyen loi", "phuc loi", "benefit")):
            if not fields["benefits"]:
                fields["benefits"] = text
        elif "ky nang" in label or "skills" in label:
            skills.extend(line.lstrip("-• ").strip() for line in text.splitlines() if line.strip())

    page_text = helper.clean_multiline_text(soup.get_text("\n", strip=True))
    if not fields["description"]:
        # Some JobsGO pages put the section label and content in a shared panel.
        fields["description"] = _text_after_label(page_text, ("Mô tả công việc", "Chi Tiết Công Việc"))
    if not fields["requirements"]:
        fields["requirements"] = _text_after_label(page_text, ("Yêu cầu công việc", "Yêu cầu"))
    if not fields["benefits"]:
        fields["benefits"] = _text_after_label(page_text, ("Quyền lợi được hưởng", "Quyền lợi"))

    return {
        **empty,
        **fields,
        "skills": list(dict.fromkeys(skill for skill in skills if skill)),
    }


def _text_after_label(page_text: str, labels: tuple[str, ...]) -> str:
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    normalized_labels = {_normalize(label) for label in labels}
    for index, line in enumerate(lines):
        normalized = _normalize(line).rstrip(":")
        if normalized in normalized_labels:
            collected = []
            for candidate in lines[index + 1:]:
                if _normalize(candidate).rstrip(":") in {
                    _normalize("Yêu cầu công việc"),
                    _normalize("Quyền lợi được hưởng"),
                    _normalize("Quyền lợi"),
                    _normalize("Thông tin chung"),
                    _normalize("Ngành nghề"),
                }:
                    break
                collected.append(candidate)
            return "\n".join(collected).strip()
    return ""
