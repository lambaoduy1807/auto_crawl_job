import scrapy


class JobItem(scrapy.Item):
    # Basic information
    title = scrapy.Field()
    company = scrapy.Field()
    url = scrapy.Field()

    # Listing information
    salary = scrapy.Field()
    location = scrapy.Field()
    working_model = scrapy.Field()
    experience = scrapy.Field()
    skills = scrapy.Field()

    # Detail information
    description = scrapy.Field()
    requirements = scrapy.Field()
    benefits = scrapy.Field()

    # Metadata
    source = scrapy.Field()
    crawled_at = scrapy.Field()
    posted_at = scrapy.Field()