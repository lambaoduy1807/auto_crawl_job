import os

from dotenv import load_dotenv

load_dotenv()


def get_list_env(key: str) -> list[str]:
    value = os.getenv(key, "")

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


ITVIEC_BASE_URL = os.getenv(
    "ITVIEC_BASE_URL",
    "https://itviec.com"
)

ITVIEC_JOBS_PATH = os.getenv(
    "ITVIEC_JOBS_PATH",
    "/it-jobs/ho-chi-minh-hcm"
)

ITVIEC_SOURCE_NAME = os.getenv(
    "ITVIEC_SOURCE_NAME",
    "ITviec"
)

ITVIEC_WORKING_MODELS = set(
    get_list_env("ITVIEC_WORKING_MODELS")
)

ITVIEC_CITIES = set(
    get_list_env("ITVIEC_CITIES")
)

ITVIEC_EXPERIENCE_LEVELS = get_list_env(
    "ITVIEC_EXPERIENCE_LEVELS"
)

ITVIEC_FRESHER_KEYWORD = os.getenv(
    "ITVIEC_FRESHER_KEYWORD",
    "fresher accepted"
)
ITVIEC_MAX_JOBS = int(
    os.getenv("ITVIEC_MAX_JOBS", "50")
)
ITVIEC_MAX_JOB_AGE_HOURS = int(
    os.getenv("ITVIEC_MAX_JOB_AGE_HOURS", "48")
)
ITVIEC_KEYWORDS = get_list_env(
    "ITVIEC_KEYWORDS"
)
