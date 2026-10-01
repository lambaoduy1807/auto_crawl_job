"""Saramin Crawl4AI entry point."""

import asyncio
import json
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig

import config
from extract_job import crawl_jobs
from extract_job_detail import extract_job_detail


JOB_FIELDS = (
    "title", "company", "url", "salary", "location", "working_model",
    "experience", "description", "requirements", "benefits", "posted_at",
    "source", "skills",
)


def save_jobs(jobs: list[dict]) -> None:
    with open(config.OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(jobs, file, ensure_ascii=False, indent=2)


async def main() -> None:
    browser_config = BrowserConfig(headless=config.HEADLESS, verbose=config.VERBOSE)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        cards = await crawl_jobs(
            crawler=crawler,
            keywords=config.KEYWORDS,
            max_jobs=config.MAX_JOBS,
            max_job_age_hours=config.MAX_JOB_AGE_HOURS,
            max_pages_per_keyword=config.MAX_PAGES_PER_KEYWORD,
        )
        jobs = []
        for index, job in enumerate(cards, start=1):
            try:
                detail = await extract_job_detail(crawler, job["url"])
                for key, value in detail.items():
                    if value and (not job.get(key)):
                        job[key] = value
            except Exception as error:
                print(f"Saramin detail failed for {job.get('url')}: {error}")

            normalized = {field: job.get(field) for field in JOB_FIELDS}
            normalized["source"] = "Saramin"
            normalized["skills"] = normalized["skills"] or []
            for field in JOB_FIELDS:
                if normalized[field] is None:
                    normalized[field] = ""
            jobs.append(normalized)
            save_jobs(jobs)

        save_jobs(jobs)
        print(f"Saramin result: {len(jobs)} jobs saved to {config.OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
