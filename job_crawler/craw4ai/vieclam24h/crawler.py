import asyncio
import json
import config
from extract_job_detail import extract_job_detail
from extract_job import crawl_jobs

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
)


# ============================================================
# SAVE JSON
# ============================================================

def save_jobs_to_json(jobs, filename="jobs.json"):
    """
    Lưu danh sách jobs vào file JSON.
    """

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            jobs,
            f,
            ensure_ascii=False,
            indent=4
        )



# ============================================================
# MAIN CRAWLER
# ============================================================

async def main():

    browser_config = BrowserConfig(
        headless=config.HEADLESS,
        verbose=config.VERBOSE,
    )

    async with AsyncWebCrawler(
        config=browser_config
    ) as crawler:

        # ====================================================
        # STEP 1
        # Crawl job list
        # ====================================================

        job_cards = await crawl_jobs(
            crawler=crawler,

            keywords=config.KEYWORDS,

            max_jobs=config.MAX_JOBS,

            max_job_age_hours=config.MAX_JOB_AGE_HOURS,

            max_pages_per_keyword=config.MAX_PAGES_PER_KEYWORD,
        )

        if not job_cards:

            print(f"Vieclam24h result: 0 jobs saved to {config.OUTPUT_FILE}")

            return

        # ====================================================
        # STEP 2
        # Crawl detail từng job
        # ====================================================

        jobs = []
        for index, job in enumerate(
            job_cards,
            start=1
        ):



            try:

                # --------------------------------------------
                # Crawl detail
                # --------------------------------------------

                detail = await extract_job_detail(
                    crawler=crawler,
                    url=job["url"],
                )

                # --------------------------------------------
                # Merge detail vào job
                # --------------------------------------------

                job.update(detail)

                # --------------------------------------------
                # Add vào danh sách kết quả
                # --------------------------------------------

                jobs.append(job)


            except Exception as e:

                print(
                    f"❌ Lỗi crawl detail job "
                    f"{index}: {e}"
                )

                # --------------------------------------------
                # Nếu detail lỗi vẫn lưu job card
                # --------------------------------------------

                job.update({
                    "experience": "",
                    "description": "",
                    "requirements": "",
                    "benefits": "",
                })

                jobs.append(job)

            # -----------------------------------------------
            # Lưu JSON sau mỗi job
            # -----------------------------------------------

            save_jobs_to_json(
                jobs,
                config.OUTPUT_FILE
            )

        # ====================================================
        # STEP 3
        # Final save
        # ====================================================

        save_jobs_to_json(
            jobs,
            config.OUTPUT_FILE
        )

        # ====================================================
        # SUMMARY
        # ====================================================

        print(f"Vieclam24h result: {len(jobs)} jobs saved to {config.OUTPUT_FILE}")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
