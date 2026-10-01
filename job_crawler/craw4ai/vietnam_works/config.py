"""Compatibility adapter to the shared Crawl4AI configuration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common_config as shared_config

_settings = shared_config.source_config("vietnam_works")
BASE_URL = _settings["base_url"]
START_URL = _settings["start_url"]
OUTPUT_FILE = _settings["output_file"]
MAX_JOBS = _settings["max_jobs"]
LIST_PAGE_WAIT = shared_config.LIST_PAGE_WAIT
DETAIL_PAGE_WAIT = shared_config.DETAIL_PAGE_WAIT
KEYWORDS = shared_config.KEYWORDS
HEADLESS = shared_config.HEADLESS
VERBOSE = shared_config.VERBOSE
MAX_JOB_AGE_HOURS = shared_config.MAX_JOB_AGE_HOURS
MAX_PAGES_PER_KEYWORD = _settings["max_pages"]

