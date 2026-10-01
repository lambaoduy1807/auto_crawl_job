"""Extract structured fields from Saramin detail pages."""

import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup
from crawl4ai import CacheMode, CrawlerRunConfig

import config
import helper


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFD", (value or "").casefold())
    return "".join(char for char in value if unicodedata.category(char) != "Mn")


def _content_text(node) -> str:
    if not node:
        return ""
    items = [helper.clean_text(li.get_text(" ", strip=True)) for li in node.select("li")]
    items = [item for item in items if item]
    if items:
        return "\n".join(f"- {item}" for item in items)
    return helper.clean_multiline_text(node.get_text("\n", strip=True))


async def extract_job_detail(crawler, url: str) -> dict:
    empty = {
        "experience": "", "description": "", "requirements": "", "benefits": "",
        "working_model": "", "location": "", "skills": [],
    }
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="domcontentloaded",
        delay_before_return_html=config.DETAIL_PAGE_WAIT,
        magic=True,
    )
    result = await crawler.arun(url=url, config=run_config)
    if not result.success or not result.html:
        print(f"Saramin detail crawl failed: {result.error_message}")
        return empty

    soup = BeautifulSoup(result.html, "html.parser")
    fields = empty.copy()
    fields["skills"] = []

    location_pattern = re.compile(r"(?:ho chi minh|ha noi|da nang|thanh pho|tinh |quan |thu duc|remote|oversea)", re.I)
    fields["location"] = next((
        helper.clean_text(node.get_text(" ", strip=True))
        for node in soup.select("span")
        if location_pattern.search(_normalized(node.get_text(" ", strip=True)))
    ), "")

    page_text = helper.clean_multiline_text(soup.get_text("\n", strip=True))
    experience_pattern = re.compile(r"\b\d+\s*(?:years?|months?|nam|thang)(?:\s*(?:-|\u2013|to)\s*\d+\s*(?:years?|months?|nam|thang))?(?:\s*,\s*\d+\s*(?:years?|months?|nam|thang))*(?:\s+(?:of\s+)?(?:experience|kinh nghiem))?\b", re.I)
    fields["experience"] = next((
        helper.clean_text(node.get_text(" ", strip=True))
        for node in soup.select("span")
        if experience_pattern.fullmatch(_normalized(helper.clean_text(node.get_text(" ", strip=True))))
    ), "")
    if not fields["experience"]:
        experience_match = experience_pattern.search(_normalized(page_text))
        if experience_match:
            fields["experience"] = experience_match.group(0).strip()

    fields["working_model"] = next((
        helper.clean_text(node.get_text(" ", strip=True))
        for node in soup.select("span")
        if re.search(r"full.?time|part.?time|remote|hybrid|on.?site|contract|truc tiep", _normalized(node.get_text(" ", strip=True)), re.I)
    ), "")
    sections = {"description": [], "requirements": [], "benefits": []}
    heading_kind = None
    for heading in soup.select('span[class*="font-semibold"][class*="text-[#3659B3]"]'):
        label = _normalized(helper.clean_text(heading.get_text(" ", strip=True)))
        if "vai tro" in label or "trach nhiem" in label or "responsibilit" in label or "your role" in label:
            heading_kind = "description"
        elif "ky nang" in label or "trinh do" in label or "yeu cau" in label or "qualification" in label or "skill" in label:
            heading_kind = "requirements"
        elif "quyen loi" in label or "phuc loi" in label or "benefit" in label:
            heading_kind = "benefits"
        else:
            heading_kind = None

        if not heading_kind:
            continue
        sibling = heading.find_next_sibling()
        while sibling and sibling.name != "span":
            if sibling.select_one(".prose-ul"):
                value = _content_text(sibling.select_one(".prose-ul"))
                if value:
                    sections[heading_kind].append(value)
            elif "prose-ul" in sibling.get("class", []):
                value = _content_text(sibling)
                if value:
                    sections[heading_kind].append(value)
            sibling = sibling.find_next_sibling()

    # The introductory paragraph precedes section 1 on Saramin; retain it with the duties.
    first_heading = next((
        node for node in soup.select('span[class*="font-semibold"][class*="text-[#3659B3]"]')
        if any(term in _normalized(node.get_text(" ", strip=True)) for term in ("vai tro", "trach nhiem", "your role", "responsibilit"))
    ), None)
    if first_heading:
        intro = first_heading.find_previous_sibling()
        intro_text = _content_text(intro) if intro and intro.name == "div" and not intro.select_one(".prose-ul") else ""
        if intro_text:
            sections["description"].insert(0, intro_text)
    for key, values in sections.items():
        fields[key] = "\n".join(dict.fromkeys(values))

    # Skill chips are links to searches and sit alongside the detail header.
    fields["skills"] = list(dict.fromkeys(
        helper.clean_text(tag.get_text(" ", strip=True))
        for tag in soup.select('a[href*="/jobs/search"]')
        if helper.clean_text(tag.get_text(" ", strip=True))
    ))
    return fields
