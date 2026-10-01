"""Central configuration for all Crawl4AI job sources."""

import os

KEYWORDS = ["Java","Intern", "Internship", "fresher", "Fresher"]
HEADLESS = True
VERBOSE = False
MAX_JOB_AGE_HOURS = 24
MAX_PAGES_PER_KEYWORD = 3
LIST_PAGE_WAIT = 2
DETAIL_PAGE_WAIT = 1

SOURCES = {
    "itviec": {
        "base_url": "https://itviec.com",
        "start_url": "https://itviec.com/it-jobs/ho-chi-minh-hcm",
        "output_file": "jobs.json",
        "max_jobs": 10,
        "max_pages": 3,
    },
    "vieclam24h": {
        "base_url": "https://vieclam24h.vn/",
        "start_url": "https://vieclam24h.vn/viec-lam-it-phan-mem-tai-tp-hcm-o8p122.html?experience_range=2",
        "output_file": "vieclam24h_jobs.json",
        "max_jobs": 15,
        "max_pages": 3,
    },
    "vietnam_works": {
        "base_url": "https://www.vietnamworks.com/",
        "start_url": "https://www.vietnamworks.com/viec-lam?l=29.11&i=25",
        "output_file": "vietnamworks_jobs.json",
        "max_jobs": 10,
        "max_pages": 3,
    },
    "jobgo": {
        "base_url": "https://jobsgo.vn",
        "start_url": "https://jobsgo.vn/viec-lam-cong-nghe-thong-tin-tai-ho-chi-minh.html",
        "output_file": "jobgo_jobs.json",
        "max_jobs": 10,
        "max_pages": 3,
    },
    "saramin": {
        "base_url": "https://saramin.vn/",
        "start_url": "https://saramin.vn/jobs/search?job_categories_ids=2&region_ids=79&ordering=newest_refresh&keyword=",
        "output_file": "saramin_jobs.json",
        "max_jobs": 5,
        "max_pages": 2,
    },
}


def source_config(source: str) -> dict:
    settings = SOURCES[source].copy()
    settings["output_file"] = os.getenv("CRAWL_OUTPUT_FILE", settings["output_file"])
    return settings
