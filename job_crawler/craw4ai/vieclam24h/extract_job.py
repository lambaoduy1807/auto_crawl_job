from crawl4ai import CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import config
import helper
import re
from pathlib import Path

# ============================================================
# PARSE JOB AGE
# ============================================================

def _parse_posted_age_hours_legacy(posted_at: str) -> float | None:
    if not posted_at:
        return None
    text = posted_at.lower().strip()
    match = re.search(r"(\d+)\s*(phút|minute|minutes)", text, re.IGNORECASE)
    if match:
        return int(match.group(1)) / 60
    match = re.search(r"(\d+)\s*(giờ|hour|hours)", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    match = re.search(r"(\d+)\s*(ngày|day|days)", text, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 24
    match = re.search(r"(\d+)\s*(tuần|week|weeks)", text, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 24 * 7
    if "\u0068\u00f4\u006d \u006e\u0061\u0079" in text or "today" in text or "\u006d\u1edb\u0069" in text or "just posted" in text:
        return 0
    return None


def extract_posted_at(card) -> str:
    """Extract a relative publication time from the card text."""
    text = helper.clean_text(card.get_text(" ", strip=True))
    match = re.search(
        r"(?:(?:\u0111\u0103ng|c\u1eadp nh\u1eadt|posted|updated)\s*)?(?:\d+\s*(?:ph\u00fat|gi\u1edd|ng\u00e0y|tu\u1ea7n|th\u00e1ng|minute|minutes|hour|hours|day|days|week|weeks|month|months)\s*(?:tr\u01b0\u1edbc|ago)|(?:h\u00f4m nay|today|m\u1edbi|just posted))",
        text,
        re.IGNORECASE,
    )
    return helper.clean_text(match.group(0)) if match else ""

# ============================================================
# NORMALIZE URL
# ============================================================

def parse_vieclam_posted_age_hours(posted_at: str) -> float | None:
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


def _normalize_title_keywords(keywords: list[str] | None) -> list[str]:
    normalized = [
        helper.clean_text(keyword).casefold()
        for keyword in (keywords or [])
        if helper.clean_text(keyword)
    ]
    # The listing uses Vietnamese titles such as "Thực Tập Sinh" for intern roles.
    if any(keyword in {"intern", "internship"} for keyword in normalized):
        normalized.append("th\u1ef1c t\u1eadp")
    if "fresher" in normalized:
        normalized.extend(("m\u1edbi t\u1ed1t nghi\u1ec7p", "ng\u01b0\u1eddi m\u1edbi t\u1ed1t nghi\u1ec7p"))
    return list(dict.fromkeys(normalized))

def normalize_job_url(url: str) -> str:
    if not url:
        return ""
    full_url = helper.get_absolute_url(url)
    if not full_url:
        return ""
    parsed = urlsplit(full_url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))

# ============================================================
# BUILD URL
# ============================================================

def build_vieclam24h_url(page: int) -> str:
    parsed = urlsplit(config.START_URL)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
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
    result = await crawler.arun(url=url, config=run_config)
    if not result.success:
        print("❌ Crawl thất bại")
        print(result.error_message)
        return []

    html = result.html
    if not html:
        print("❌ Không có HTML")
        return []

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('a[data-job-id][href]')
    if not cards:
        return []

    if seen_urls is None:
        seen_urls = set()

    normalized_keywords = _normalize_title_keywords(title_keywords)

    jobs = []
    for index, card in enumerate(cards, start=1):
        job_id = helper.clean_text(card.get("data-job-id", ""))
        href = card.get("href", "")
        if not href:
            continue
        full_url = normalize_job_url(href)
        if not full_url:
            continue
        if full_url in seen_urls:
            continue

        h3_tags = card.find_all("h3")
        if not h3_tags:
            continue
        title = helper.clean_text(h3_tags[0].get_text(" ", strip=True))
        if not title:
            continue

        if normalized_keywords:
            title_lower = title.lower()
            matched = any(keyword in title_lower for keyword in normalized_keywords)
            if not matched:
                continue

        posted_at = extract_posted_at(card)
        age_hours = parse_vieclam_posted_age_hours(posted_at)
        # Listing HTML has expiry dates but no posting timestamp, so unknown age is retained.
        if age_hours is not None and age_hours > max_job_age_hours:
            continue

        company = ""
        if len(h3_tags) >= 2:
            company = helper.clean_text(h3_tags[1].get_text(" ", strip=True))

        salary = ""
        salary_icon = card.select_one("i.svicon-money-circle")
        if salary_icon:
            salary_container = salary_icon.find_parent("div")
            if salary_container:
                salary_element = salary_container.find("span")
                if salary_element:
                    salary = helper.clean_text(salary_element.get_text(" ", strip=True))

        location = ""
        location_container = card.select_one("div.province-tooltip")
        if location_container:
            location_element = location_container.select_one("span:not(.tooltip-content)")
            if location_element:
                location = helper.clean_text(location_element.get_text(" ", strip=True))

        deadline = ""
        clock_icon = card.select_one("i.svicon-clock")
        if clock_icon:
            clock_container = clock_icon.find_parent("div")
            if clock_container:
                deadline_element = clock_container.find(
                    class_=lambda classes: classes and "text-14" in classes if isinstance(classes, list) else False
                )
                if deadline_element:
                    deadline = helper.clean_text(deadline_element.get_text(" ", strip=True))

        deadline_date = ""
        deadline_text = card.get_text(" ", strip=True)
        deadline_match = re.search(
            r"Ng\u00e0y h\u1ebft h\u1ea1n n\u1ed9p h\u1ed3 s\u01a1\s*(\d{1,2}/\d{1,2}/\d{4})",
            deadline_text,
            re.IGNORECASE,
        )
        if deadline_match:
            deadline_date = deadline_match.group(1)

        experience_match = re.search(
            r"(?:d\u01b0\u1edbi\s+|tr\u00ean\s+)?\d+\s*\+?\s*(?:n\u0103m|th\u00e1ng)(?:\s+kinh\s+nghi\u1ec7m)?",
            deadline_text,
            re.IGNORECASE,
        )
        experience = helper.clean_text(experience_match.group(0)) if experience_match else ""
        seen_urls.add(full_url)
        job = {
            "job_id": job_id,
            "title": title,
            "company": company,
            "url": full_url,
            "salary": salary,
            "location": location,
            "working_model": "",
            "experience": experience,
            "description": "",
            "requirements": "",
            "benefits": "",
            "posted_at": posted_at,
            "deadline": deadline,
            "deadline_date": deadline_date,
            "source": "Vieclam24h",
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
    max_job_age_hours: int = 24, # kept for compatibility with crawler.py
    max_pages_per_keyword: int = 20,
):
    all_jobs = []
    seen_urls = set()

    for keyword in [", ".join(keywords)]:
        if len(all_jobs) >= max_jobs:
            break
        keyword = keyword.strip()
        if not keyword:
            continue

        for page in range(1, max_pages_per_keyword + 1):
            if len(all_jobs) >= max_jobs:
                break

            url = build_vieclam24h_url(page=page)
            jobs = await extract_job_cards(
                crawler=crawler,
                url=url,
                title_keywords=keywords,
                max_job_age_hours=max_job_age_hours,
                seen_urls=seen_urls,
            )

            if not jobs:
                continue

            remaining = max_jobs - len(all_jobs)
            all_jobs.extend(jobs[:remaining])

            if len(all_jobs) >= max_jobs:
                break

    return all_jobs
