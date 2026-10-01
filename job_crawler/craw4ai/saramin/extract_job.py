"""Saramin job-list extraction for the current Saramin listing markup."""

import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from crawl4ai import CacheMode, CrawlerRunConfig

import config
import helper


def parse_posted_age_hours(posted_at: str) -> float | None:
    text = (posted_at or "").casefold().strip()
    patterns = (
        (r"(\d+)\s*(?:phút|minutes?)\b", 1 / 60),
        (r"(\d+)\s*(?:giờ|hours?)\b", 1),
        (r"(\d+)\s*(?:ngày|days?)\b", 24),
        (r"(\d+)\s*(?:tuần|weeks?)\b", 168),
        (r"(\d+)\s*(?:tháng|months?)\b", 720),
    )
    for pattern, multiplier in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1)) * multiplier
    if any(token in text for token in ("hôm nay", "today", "just posted")):
        return 0
    return None


def _search_url(page: int) -> str:
    parsed = urlsplit(config.START_URL)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.pop("keyword", None)
    if page > 1:
        params["page"] = str(page)
    return f"{config.BASE_URL.rstrip('/')}/jobs/search?{urlencode(params)}"


def _absolute_url(url: str, page_url: str) -> str:
    absolute = urljoin(page_url or config.BASE_URL, (url or "").strip())
    parsed = urlsplit(absolute)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _span_texts(card) -> list[str]:
    return list(dict.fromkeys(
        helper.clean_text(node.get_text(" ", strip=True))
        for node in card.select("span")
        if helper.clean_text(node.get_text(" ", strip=True))
    ))


def _find_value(card, pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    matches = [
        text for text in _span_texts(card)
        if regex.search(text)
    ]
    return min(matches, key=len) if matches else ""


async def extract_job_cards(
    crawler,
    url: str,
    title_keywords: list[str] | None = None,
    max_job_age_hours: int = 24,
    seen_urls: set[str] | None = None,
) -> list[dict]:
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="domcontentloaded",
        delay_before_return_html=config.LIST_PAGE_WAIT,
        magic=True,
    )
    result = await crawler.arun(url=url, config=run_config)
    if not result.success or not result.html:
        print(f"Saramin list crawl failed: {result.error_message}", flush=True)
        return []

    soup = BeautifulSoup(result.html, "html.parser")
    seen_urls = seen_urls if seen_urls is not None else set()
    keywords = [word.casefold().strip() for word in (title_keywords or []) if word.strip()]
    job_links = soup.select('a[href^="/detail-jobs/"]')

    jobs = []
    for link in job_links:
        title = helper.clean_text(link.get_text(" ", strip=True))
        if not title or (keywords and not any(word in title.casefold() for word in keywords)):
            continue

        job_url = _absolute_url(link.get("href", ""), page_url=url)
        if not job_url or job_url in seen_urls:
            continue

        # Listing cards in the captured HTML use this wrapper class.
        card = link.find_parent("div", class_="text-card-foreground")
        if card is None:
            continue

        texts = _span_texts(card)
        posted_at = next((
            text for text in texts
            if re.search(
                r"\b\d+\s*(?:minutes?|hours?|days?|weeks?|months?)\s+ago\b"
                r"|\b(?:today|just posted)\b"
                r"|\b\d+\s*(?:phút|giờ|ngày|tuần|tháng)\b",
                text,
                re.I,
            )
        ), "")
        age_hours = parse_posted_age_hours(posted_at)
        if age_hours is not None and age_hours > max_job_age_hours:
            continue

        company_node = link.find_next_sibling("span")
        company = helper.clean_text(company_node.get_text(" ", strip=True)) if company_node else ""

        salary_node = card.select_one('span[class*="text-[#e4007f]"]')
        salary = helper.clean_text(salary_node.get_text(" ", strip=True)) if salary_node else ""
        if "login to view" in salary.casefold():
            salary = ""
        if not salary:
            salary = _find_value(card, r"thương lượng|negotiable|\d[\d.,]*\s*(?:triệu|tr\b|million|usd|vnd)")

        location = next((
            text for text in texts
            if re.search(
                r"Hồ Chí Minh|Hà Nội|Đà Nẵng|Thành phố|Tỉnh |Quận |Thủ Đức|Remote|Oversea",
                text,
                re.I,
            )
        ), "")
        working_model = next((
            text for text in texts
            if re.search(r"full.?time|part.?time|remote|hybrid|on.?site|contract", text, re.I)
        ), "")
        experience = next((
            text for text in texts
            if re.search(r"\b\d+\s*(?:years?|năm|tháng)(?:\s+(?:experience|kinh nghiệm))?\b", text, re.I)
        ), "")

        skills = list(dict.fromkeys(
            helper.clean_text(tag.get_text(" ", strip=True))
            for tag in card.select('a[href*="keyword="]')
            if helper.clean_text(tag.get_text(" ", strip=True))
        ))

        seen_urls.add(job_url)
        job = {
            "title": title,
            "company": company,
            "url": job_url,
            "salary": salary,
            "location": location,
            "working_model": working_model,
            "experience": experience,
            "description": "",
            "requirements": "",
            "benefits": "",
            "posted_at": posted_at,
            "source": "Saramin",
            "skills": skills,
        }
        jobs.append(job)

    return jobs


async def crawl_jobs(
    crawler,
    keywords: list[str],
    max_jobs: int,
    max_job_age_hours: int = 24,
    max_pages_per_keyword: int = 20,
) -> list[dict]:
    jobs = []
    seen_urls: set[str] = set()
    for _keyword in [", ".join(keywords)]:
        for page in range(1, max_pages_per_keyword + 1):
            if len(jobs) >= max_jobs:
                return jobs[:max_jobs]
            found = await extract_job_cards(
                crawler, _search_url(page), keywords, max_job_age_hours, seen_urls
            )
            jobs.extend(found[:max_jobs - len(jobs)])
    return jobs[:max_jobs]
