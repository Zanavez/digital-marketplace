# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class MarketParserItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    title = scrapy.Field()
    current_price = scrapy.Field()
    original_price = scrapy.Field()
    url = scrapy.Field()
    description = scrapy.Field()
    release_date = scrapy.Field()
    developer = scrapy.Field()
    publisher = scrapy.Field()
