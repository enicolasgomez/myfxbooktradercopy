# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class Operation(scrapy.Item):
    hashid      = scrapy.Field()
    timeOrderDiscovered = scrapy.Field()
    timeTradeOpened     = scrapy.Field()
    timeTradeClosed     = scrapy.Field()
    timeTradeAttempedOpened = scrapy.Field()
    symbol      = scrapy.Field()
    action      = scrapy.Field()
    lots        = scrapy.Field()
    openPrice   = scrapy.Field()
    closePrice  = scrapy.Field()
    url         = scrapy.Field()
    profit      = scrapy.Field()
    orderid     = scrapy.Field()
    tradeid     = scrapy.Field()
