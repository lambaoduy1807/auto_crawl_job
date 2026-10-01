"""JobsGO list page extraction and recent-post filtering."""

import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from crawl4ai import CacheMode, CrawlerRunConfig

import config
import helper


def parse_posted_age_hours(posted_at: str) -> float | None:
    text = (posted_at or "").lower().strip()
    patterns = (
        (r"(\d+)\s*(?:ph\u00fat|minute|minutes)", 1 / 60),
        (r"(\d+)\s*(?:gi\u1edd|hour|hours)", 1),
        (r"(\d+)\s*(?:ng\u00e0y|day|days)", 24),
        (r"(\d+)\s*(?:tu\u1ea7n|week|weeks)", 24 * 7),
        (r"(\d+)\s*(?:th\u00e1ng|month|months)", 24 * 30),
    )
    for pattern, factor in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1)) * factor
    if any(value in text for value in ("h\u00f4m nay", "today", "m\u1edbi", "just posted")):
        return 0
    return None


def build_jobsgo_url(page: int) -> str:
    parsed = urlsplit(config.START_URL)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if page > 1:
        params["page"] = str(page)
    else:
        params.pop("page", None)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(params), ""))


def _absolute_job_url(url: str) -> str:
    absolute = helper.get_absolute_url(url)
    parsed = urlsplit(absolute)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _card_badge(card, title: str) -> str:
    title = title.casefold()
    for badge in card.select("span[title]"):
        if (badge.get("title") or "").strip().casefold() == title:
            return helper.clean_text(badge.get_text(" ", strip=True))
    return ""


async def extract_job_cards(
    crawler,
    url: str,
    title_keywords: list[str] | None = None,
    max_job_age_hours: int = 24,
    seen_urls: set[str] | None = None,
) -> list[dict] | None:
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="domcontentloaded",
        delay_before_return_html=config.LIST_PAGE_WAIT,
        magic=True,
    )
    result = await crawler.arun(url=url, config=run_config)
    if not result.success or not result.html:
        print(f"JobsGO list crawl failed: {result.error_message}")
        return None

    soup = BeautifulSoup(result.html, "html.parser")
    cards = soup.select(".job-list .job-card") or soup.select(".job-card")
    if seen_urls is None:
        seen_urls = set()
    normalized_keywords = [word.casefold().strip() for word in (title_keywords or []) if word.strip()]
    jobs = []

    for card in cards:
        title_link = card.select_one("h3.job-title a[href]")
        if not title_link:
            continue
        title = helper.clean_text(title_link.get("title") or title_link.get_text(" ", strip=True))
        if not title or (normalized_keywords and not any(key in title.casefold() for key in normalized_keywords)):
            continue

        posted_at = _card_badge(card, "Thời gian cập nhật")
        age_hours = parse_posted_age_hours(posted_at)
        if age_hours is None or age_hours > max_job_age_hours:
            continue

        url = _absolute_job_url(title_link.get("href", ""))
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        company_node = card.select_one("a.company-title")
        company = helper.clean_text(
            company_node.get("title") or company_node.get_text(" ", strip=True)
        ) if company_node else ""

        summary = card.select_one(".text-primary.fw-semibold")
        summary_values = [
            helper.clean_text(node.get_text(" ", strip=True))
            for node in summary.find_all("span", recursive=False)
            if helper.clean_text(node.get_text(" ", strip=True)) not in {"|", ""}
        ] if summary else []

        jobs.append({
            "title": title,
            "company": company,
            "url": url,
            "salary": summary_values[0] if summary_values else "",
            "location": summary_values[1] if len(summary_values) > 1 else "",
            "working_model": _card_badge(card, "Loại hình"),
            "experience": _card_badge(card, "Yêu cầu kinh nghiệm"),
            "description": "",
            "requirements": "",
            "benefits": "",
            "posted_at": posted_at,
            "source": "JobsGO",
            "skills": [],
        })
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
    for keyword in [", ".join(keywords)]:
        for page in range(1, max_pages_per_keyword + 1):
            if len(jobs) >= max_jobs:
                return jobs[:max_jobs]
            page_jobs = await extract_job_cards(
                crawler=crawler,
                url=build_jobsgo_url(page),
                title_keywords=keywords,
                max_job_age_hours=max_job_age_hours,
                seen_urls=seen_urls,
            )
            if page_jobs is None:
                # A failed request (for example HTTP 403) is different from a valid
                # page with no matching titles. Stop to avoid repeating blocked requests.
                return jobs[:max_jobs]
            if not page_jobs:
                continue
            jobs.extend(page_jobs[:max_jobs - len(jobs)])
    return jobs[:max_jobs]
