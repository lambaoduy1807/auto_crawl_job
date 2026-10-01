"""JobsGO Crawl4AI entry point."""

import asyncio
import json

import config
from crawl4ai import AsyncWebCrawler, BrowserConfig
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
from crawl4ai.browser_adapter import UndetectedAdapter
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
    crawler_strategy = AsyncPlaywrightCrawlerStrategy(
        browser_config=browser_config,
        browser_adapter=UndetectedAdapter(),
    )
    async with AsyncWebCrawler(
        config=browser_config,
        crawler_strategy=crawler_strategy,
    ) as crawler:
        cards = await crawl_jobs(
            crawler=crawler,
            keywords=config.KEYWORDS,
            max_jobs=config.MAX_JOBS,
            max_job_age_hours=config.MAX_JOB_AGE_HOURS,
            max_pages_per_keyword=config.MAX_PAGES_PER_KEYWORD,
        )
        jobs = []
        detail_access_blocked = False
        for index, job in enumerate(cards, start=1):
            if not detail_access_blocked:
                try:
                    detail = await extract_job_detail(
                        crawler,
                        job["url"],
                    )
                    if detail is None:
                        detail_access_blocked = True
                        print("JobsGO detail access failed; skipping remaining detail pages and keeping list data.")
                    else:
                        for key, value in detail.items():
                            if value and (key not in job or not job[key]):
                                job[key] = value
                except Exception as error:
                    print(f"JobsGO detail failed for {job.get('url')}: {error}")
            normalized = {field: job.get(field) for field in JOB_FIELDS}
            normalized["source"] = "JobsGO"
            normalized["skills"] = normalized["skills"] or []
            for field in JOB_FIELDS:
                if normalized[field] is None:
                    normalized[field] = ""
            jobs.append(normalized)
            save_jobs(jobs)
        save_jobs(jobs)
        print(f"JobsGO result: {len(jobs)} jobs saved to {config.OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
