import re

from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, urlunparse

import scrapy

from job_crawler.items import JobItem

from config.config import (
    ITVIEC_BASE_URL,
    ITVIEC_JOBS_PATH,
    ITVIEC_SOURCE_NAME,
    ITVIEC_WORKING_MODELS,
    ITVIEC_CITIES,
    ITVIEC_EXPERIENCE_LEVELS,
    ITVIEC_KEYWORDS,
    ITVIEC_FRESHER_KEYWORD,
    ITVIEC_MAX_JOBS,
    ITVIEC_MAX_JOB_AGE_HOURS,
)


class ItviecSpider(scrapy.Spider):

    name = "itviec"

    allowed_domains = [
        urlparse(ITVIEC_BASE_URL).netloc
    ]

    start_urls = [
        f"{ITVIEC_BASE_URL}{ITVIEC_JOBS_PATH}"
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 1,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.job_count = 0
        self.seen_urls = set()

        self.cutoff_time = (
            datetime.now()
            - timedelta(hours=ITVIEC_MAX_JOB_AGE_HOURS)
        )

        self.logger.info(
            "Max jobs: %s",
            ITVIEC_MAX_JOBS
        )

        self.logger.info(
            "Max job age: %s hours",
            ITVIEC_MAX_JOB_AGE_HOURS
        )

        self.logger.info(
            "Keywords: %s",
            ITVIEC_KEYWORDS
        )

        self.logger.info(
            "Experience levels: %s",
            ITVIEC_EXPERIENCE_LEVELS
        )

    # ============================================================
    # PARSE LISTING PAGE
    # ============================================================

    def parse(self, response):

        if response.status != 200:
            self.logger.warning(
                "Listing failed: %s - HTTP %s",
                response.url,
                response.status
            )
            return

        if self.job_count >= ITVIEC_MAX_JOBS:
            self.logger.info(
                "Reached maximum jobs: %s",
                ITVIEC_MAX_JOBS
            )
            return

        cards = response.css("div.job-card")

        self.logger.info(
            "Found %s job cards at %s",
            len(cards),
            response.url
        )

        for card in cards:

            if self.job_count >= ITVIEC_MAX_JOBS:
                break

            listing_data = self.parse_listing_card(card)

            job_url = self.extract_job_url(card)

            if not job_url:
                continue

            job_url = self.normalize_url(job_url)

            if job_url in self.seen_urls:
                continue

            self.seen_urls.add(job_url)

            # ----------------------------------------------------
            # Filter by posted time
            # ----------------------------------------------------

            posted_at = self.extract_posted_at(card)

            if posted_at is None:
                self.logger.debug(
                    "Cannot detect posted time: %s",
                    job_url
                )

            elif posted_at < self.cutoff_time:
                self.logger.debug(
                    "Skip old job: %s - posted at %s",
                    listing_data.get("title"),
                    posted_at
                )
                continue

            # ----------------------------------------------------
            # Filter by keyword
            # ----------------------------------------------------

            if not self.matches_keywords(listing_data):
                self.logger.debug(
                    "Skip keyword mismatch: %s",
                    listing_data.get("title")
                )
                continue

            # ----------------------------------------------------
            # Filter by location
            # ----------------------------------------------------

            if not self.matches_location(
                listing_data.get("location")
            ):
                self.logger.debug(
                    "Skip location mismatch: %s",
                    listing_data.get("title")
                )
                continue

            # ----------------------------------------------------
            # Filter by working model
            # ----------------------------------------------------

            if (
                ITVIEC_WORKING_MODELS
                and listing_data.get("working_model")
                and listing_data.get("working_model")
                not in ITVIEC_WORKING_MODELS
            ):
                self.logger.debug(
                    "Skip working model mismatch: %s",
                    listing_data.get("title")
                )
                continue

            self.job_count += 1

            self.logger.info(
                "Request job %s/%s: %s",
                self.job_count,
                ITVIEC_MAX_JOBS,
                listing_data.get("title")
            )

            yield scrapy.Request(
                url=job_url,
                callback=self.parse_detail,
                meta={
                    "listing_data": listing_data,
                    "posted_at": posted_at.isoformat()
                    if posted_at
                    else None,
                },
                dont_filter=False,
            )

        # --------------------------------------------------------
        # Pagination
        # --------------------------------------------------------

        if self.job_count >= ITVIEC_MAX_JOBS:
            return

        next_url = self.extract_next_page(response)

        if next_url:
            self.logger.info(
                "Next page: %s",
                next_url
            )

            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
            )

    # ============================================================
    # PARSE LISTING CARD
    # ============================================================

    def parse_listing_card(self, card):

        title = card.css(
            "h3 a::text"
        ).get()

        if not title:
            title = card.css(
                "h3::text"
            ).get()

        company = card.css(
            'a[href*="/companies/"]::text'
        ).get()

        salary = card.css(
            ".salary"
        ).xpath(
            "string(.)"
        ).get()

        card_text = self.get_text_lines(card)

        working_model = self.find_working_model(card_text)

        location = self.extract_location(
            card_text,
            working_model
        )

        return {
            "title": self.clean_text(title),
            "company": self.clean_text(company),
            "salary": self.clean_text(salary),
            "working_model": working_model,
            "location": location,
        }

    # ============================================================
    # KEYWORD FILTER
    # ============================================================

    def matches_keywords(self, data):

        title = data.get("title") or ""

        searchable_text = title.lower()

        # --------------------------------------------------------
        # Generic keywords from ITVIEC_KEYWORDS
        # --------------------------------------------------------

        if ITVIEC_KEYWORDS:

            has_keyword = any(
                keyword.lower() in searchable_text
                for keyword in ITVIEC_KEYWORDS
            )

            if not has_keyword:
                return False

        return True

    # ============================================================
    # LOCATION FILTER
    # ============================================================

    def matches_location(self, location):

        if not ITVIEC_CITIES:
            return True

        if not location:
            return False

        location_lower = location.lower()

        return any(
            city.lower() in location_lower
            for city in ITVIEC_CITIES
        )

    # ============================================================
    # POSTED TIME
    # ============================================================

    def extract_posted_at(self, card):

        text = " ".join(
            card.xpath(
                ".//text()[normalize-space()]"
            ).getall()
        )

        text = self.clean_text(text)

        if not text:
            return None

        text_lower = text.lower()

        now = datetime.now()

        # Posted just now
        if (
            "just now" in text_lower
            or "vừa xong" in text_lower
        ):
            return now

        # Posted X minutes ago
        match = re.search(
            r"posted\s+(\d+)\s+minute[s]?\s+ago",
            text_lower
        )

        if match:
            minutes = int(match.group(1))
            return now - timedelta(minutes=minutes)

        # Posted X hours ago
        match = re.search(
            r"posted\s+(\d+)\s+hour[s]?\s+ago",
            text_lower
        )

        if match:
            hours = int(match.group(1))
            return now - timedelta(hours=hours)

        # Posted X days ago
        match = re.search(
            r"posted\s+(\d+)\s+day[s]?\s+ago",
            text_lower
        )

        if match:
            days = int(match.group(1))
            return now - timedelta(days=days)

        # Posted today
        if "posted today" in text_lower:
            return now

        # Posted yesterday
        if "posted yesterday" in text_lower:
            return now - timedelta(days=1)

        return None

    # ============================================================
    # DETAIL PAGE
    # ============================================================

    def parse_detail(self, response):

        if response.status != 200:
            self.logger.warning(
                "Detail failed: %s - HTTP %s",
                response.url,
                response.status
            )
            return

        listing_data = response.meta.get(
            "listing_data",
            {}
        )

        posted_at = response.meta.get(
            "posted_at"
        )

        detail_text = self.clean_text(
            response.xpath(
                "string(.)"
            ).get()
        ) or ""

        # --------------------------------------------------------
        # Recheck keyword on detail page
        # --------------------------------------------------------

        if not self.matches_detail_keywords(
            listing_data,
            detail_text
        ):
            self.logger.info(
                "Skip detail keyword mismatch: %s",
                response.url
            )
            return

        item = JobItem()

        title = response.css(
            "h1::text"
        ).get()

        company = response.css(
            ".employer-name::text"
        ).get()

        salary = response.css(
            ".salary"
        ).xpath(
            "string(.)"
        ).get()

        location = self.extract_detail_location(
            response
        )

        working_model = self.extract_working_model(
            response
        )

        experience = self.extract_experience(
            response
        )

        item["title"] = (
            self.clean_text(title)
            or listing_data.get("title")
        )

        item["company"] = (
            self.clean_text(company)
            or listing_data.get("company")
        )

        item["url"] = self.normalize_url(
            response.url
        )

        item["salary"] = (
            self.clean_text(salary)
            or listing_data.get("salary")
        )

        item["working_model"] = (
            working_model
            or listing_data.get("working_model")
        )

        item["location"] = (
            location
            or listing_data.get("location")
        )

        item["experience"] = experience

        item["description"] = self.get_section(
            response,
            "Job description"
        )

        item["requirements"] = self.get_section(
            response,
            "Your skills and experience"
        )

        item["benefits"] = self.get_section(
            response,
            "Why you'll love working here"
        )

        item["source"] = ITVIEC_SOURCE_NAME

        item["posted_at"] = posted_at

        item["crawled_at"] = datetime.now().isoformat()

        yield item

    # ============================================================
    # DETAIL KEYWORD FILTER
    # ============================================================

    def matches_detail_keywords(
        self,
        listing_data,
        detail_text
    ):

        combined_text = " ".join(
            [
                listing_data.get("title") or "",
                detail_text,
            ]
        ).lower()

        if ITVIEC_KEYWORDS:

            if not any(
                keyword.lower() in combined_text
                for keyword in ITVIEC_KEYWORDS
            ):
                return False

        experience_keywords = [
            level.lower()
            for level in ITVIEC_EXPERIENCE_LEVELS
        ]

        fresher_keyword = (
            ITVIEC_FRESHER_KEYWORD or ""
        ).lower()

        if experience_keywords or fresher_keyword:

            has_experience = any(
                keyword in combined_text
                for keyword in experience_keywords
            )

            has_fresher = (
                fresher_keyword
                and fresher_keyword in combined_text
            )

            if not (
                has_experience
                or has_fresher
            ):
                return False

        return True

    # ============================================================
    # JOB URL
    # ============================================================

    def extract_job_url(self, card):

        links = card.css(
            'h3 a[href*="/it-jobs/"]::attr(href)'
        ).getall()

        if not links:
            links = card.css(
                'a[href*="/it-jobs/"]::attr(href)'
            ).getall()

        if not links:
            return None

        return urljoin(
            ITVIEC_BASE_URL,
            links[0]
        )

    # ============================================================
    # WORKING MODEL
    # ============================================================

    def find_working_model(self, lines):

        for line in lines:

            for model in ITVIEC_WORKING_MODELS:

                if model.lower() == line.lower():
                    return model

        return None

    def extract_working_model(self, response):

        text = response.text.lower()

        for model in ITVIEC_WORKING_MODELS:

            if model.lower() in text:
                return model

        return None

    # ============================================================
    # LOCATION
    # ============================================================

    def extract_location(self, lines, working_model):

        if not lines:
            return None

        if working_model:
            try:
                index = lines.index(
                    working_model
                )

                for line in lines[index + 1:]:
                    for city in ITVIEC_CITIES:

                        if city.lower() in line.lower():
                            return line

            except ValueError:
                pass

        for line in lines:
            for city in ITVIEC_CITIES:

                if city.lower() in line.lower():
                    return line

        return None

    def extract_detail_location(self, response):

        lines = self.get_text_lines(response)

        for line in lines:

            for city in ITVIEC_CITIES:

                if city.lower() in line.lower():
                    return line

        return None


    # ============================================================
    # EXPERIENCE
    # ============================================================

    def extract_experience(self, response):

        text = response.text.lower()

        for level in ITVIEC_EXPERIENCE_LEVELS:

            if level.lower() in text:
                return level

        if (
            ITVIEC_FRESHER_KEYWORD
            and ITVIEC_FRESHER_KEYWORD.lower()
            in text
        ):
            return "Fresher"

        return None

    # ============================================================
    # SECTION
    # ============================================================

    def get_section(self, response, section_name):

        headings = response.css("h2")

        for heading in headings:

            heading_text = self.clean_text(
                heading.xpath(
                    "string(.)"
                ).get()
            )

            if not heading_text:
                continue

            if heading_text.lower() != section_name.lower():
                continue

            parent = heading.xpath("..")

            content = self.clean_text(
                parent.xpath(
                    "string(.)"
                ).get()
            )

            if content and content.lower().startswith(
                section_name.lower()
            ):
                content = content[
                    len(section_name):
                ].strip()

            return content

        return None

    # ============================================================
    # PAGINATION
    # ============================================================

    def extract_next_page(self, response):

        next_link = response.css(
            'a[rel="next"]::attr(href)'
        ).get()

        if next_link:
            return urljoin(
                response.url,
                next_link
            )

        pagination_links = response.css(
            'a[href*="page="]::attr(href)'
        ).getall()

        if not pagination_links:
            return None

        current_page = self.get_current_page(
            response.url
        )

        next_page = current_page + 1

        for href in pagination_links:

            if f"page={next_page}" in href:
                return urljoin(
                    response.url,
                    href
                )

        return None

    def get_current_page(self, url):

        match = re.search(
            r"[?&]page=(\d+)",
            url
        )

        if match:
            return int(
                match.group(1)
            )

        return 1

    # ============================================================
    # TEXT HELPERS
    # ============================================================

    def get_text_lines(self, selector):

        texts = selector.xpath(
            ".//text()[normalize-space()]"
        ).getall()

        result = []

        for text in texts:

            text = self.clean_text(text)

            if text and text not in result:
                result.append(text)

        return result

    @staticmethod
    def clean_text(text):

        if not text:
            return None

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    @staticmethod
    def normalize_url(url):

        parsed = urlparse(url)

        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                "",
                "",
                ""
            )
        )