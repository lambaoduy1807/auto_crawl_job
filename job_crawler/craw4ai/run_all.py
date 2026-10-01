"""Run every Crawl4AI job crawler and combine its output into one schema."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CRAWL4AI_DIR = Path(__file__).resolve().parent
PROJECT_DIR = CRAWL4AI_DIR.parents[2]
OUTPUT_FILE = PROJECT_DIR / "jobs.json"
JOB_FIELDS = (
    "title", "company", "url", "salary", "location", "working_model",
    "experience", "description", "requirements", "benefits", "posted_at",
    "source", "skills",
)
CRAWLERS = (
    ("itviec", "ITviec"),
    ("vieclam24h", "Vieclam24h"),
    ("vietnam_works", "VietnamWorks"),
    ("jobgo", "JobsGO"),
    ("saramin", "Saramin"),
)


def run_all_crawlers() -> list[dict]:
    jobs = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="crawl4ai-") as temp_dir:
        for crawler_name, source in CRAWLERS:
            crawler_dir = CRAWL4AI_DIR / crawler_name
            result_file = Path(temp_dir) / f"{crawler_name}.json"
            env = os.environ.copy()
            env["CRAWL_OUTPUT_FILE"] = str(result_file)
            result = subprocess.run([sys.executable, "crawler.py"], cwd=crawler_dir, env=env, check=False)
            if result.returncode != 0:
                failures.append(f"{crawler_name} exited with code {result.returncode}")
                continue
            if not result_file.exists():
                continue
            with result_file.open("r", encoding="utf-8") as file:
                for job in json.load(file):
                    normalized = {field: job.get(field) for field in JOB_FIELDS}
                    normalized["source"] = job.get("source") or source
                    normalized["skills"] = job.get("skills") or []
                    for field in JOB_FIELDS:
                        if normalized[field] is None:
                            normalized[field] = ""
                    jobs.append(normalized)
    if failures:
        raise RuntimeError("Crawl4AI crawler failures: " + "; ".join(failures))
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(jobs, file, ensure_ascii=False, indent=2)
    print(f"Combined {len(jobs)} jobs into {OUTPUT_FILE}")
    return jobs


if __name__ == "__main__":
    run_all_crawlers()
