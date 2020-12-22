import scrapy
import hashlib
import os
from myfxbook.items import Operation
from persistentstore import PersistentStore
import time 
from datetime import datetime as dt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class RofxnetSpider(scrapy.Spider):
    name = 'rofxnet'
    custom_settings = {
        'ROBOTSTXT_OBEY': False
    }
    allowed_domains = ['rofxnet']
    
    #start_urls = ['https://www.myfxbook.com/members/bhuziuk/gbpcad60/6433680']

    start_urls = ['https://www.myfxbook.com/members/Dante1927/cobra/5765065'
                # , 'https://www.myfxbook.com/members/autotrade/gold-trading/3543401'
                # , 'https://www.myfxbook.com/members/lepp/gbpcad-ncm/6532319'
                # , 'https://www.myfxbook.com/members/PlatinumTDT/platinum-trading/3543497'
                 , 'https://www.myfxbook.com/members/ForexMaster01/vip-trading-club-ecn/7425929']

    #start_urls = [f"file://{BASE_DIR}/Sample/test3.html"]

    def get_hash(self, s):
        return hashlib.sha1(str.encode(s)).hexdigest()

    #['Open Date', 'Symbol', 'Action', '    Lots', 'Open Price', 'SL', 'TP, 'Profit (USD)', 'Pips', 'Swap', 'Gain']
    def get_column_index_by_name(self, columns, name):

        column_names = columns.xpath('th//a/text()').extract()
        column_names_strip = list(map(lambda x: x.strip(), column_names))
        return column_names_strip.index(name) + len(columns.xpath('th[1]//img').extract()) + 1 #add image column

    def parse(self, response):

        system_id = response.url.split("/")[-1]

        if (dt.now().minute in [0,5,10,15,25,30,35,40,45,50,55]): #log parsed html every 30 minutes
            file_name = str(dt.now())
            f = open( f"{BASE_DIR}/parsed/{system_id}-{file_name}-ALL.html","w+")
            f.write(response.text)
            f.close()

        noData = response.selector.xpath('//div[@id="openTrades"]/div/span/text()').extract_first()

        if (noData == 'No data to display.'):
            self.logger.info('No open trades found for %s', response.url)
            return
        else:
            self.logger.info('Open trades found for %s', response.url)

        operations = response.selector.xpath('//div[@id="openTrades"]/table/tr')

        if not len(operations):
            operations = response.selector.xpath('//div[@id="openTrades"]/table/tbody/tr')

        self.logger.info('Operations: ' + str(len(operations)))

        if len(operations) < 3: #header, [...], footer
            self.logger.info('Empty operations set')
        else:
            persistentstore = PersistentStore()
            persistentstore.set_inited() #are items availabe to compare for closing

            column_names = operations[0]

            for operation in operations[1:-1]: #remove header and total rows
                self.logger.info('processing operation...')

                if (dt.now().minute in [0,30]): #log parsed html every 30 minutes
                    file_name = str(dt.now())
                    f = open( f"{BASE_DIR}/parsed/{system_id}-{file_name}-OPENED.html","w+")
                    f.write(response.text)
                    f.close()

                try:
                    openDateRaw = operation.xpath(('td[not(@style="display:none")][%i]//text()' %     self.get_column_index_by_name(column_names, 'Open Date'))).extract_first().strip()
                    symbolRaw = operation.xpath(('td[not(@style="display:none")][%i]//span//text()' % self.get_column_index_by_name(column_names, 'Symbol')))   .extract_first()
                    actionRaw = operation.xpath(('td[not(@style="display:none")][%i]//text()' %       self.get_column_index_by_name(column_names, 'Action')))   .extract_first().strip()
                    lotsRaw = 5 
                    openPriceRaw = operation.xpath(('td[not(@style="display:none")][%i]//text()' %    self.get_column_index_by_name(column_names, 'Open Price'))).extract_first().strip()

                    if not openPriceRaw.strip():
                        openPriceRaw = 0
                    
                    self.logger.info('openDate: %s, symbolRaw: %s, actionRaw: %s, lotsRaw: %s, openPriceRaw: %s', openDateRaw, symbolRaw, actionRaw, lotsRaw, openPriceRaw)

                    item = Operation()
                    str_hash = str(openDateRaw) + str(symbolRaw) + str(actionRaw) + str(lotsRaw) + str(openPriceRaw) + system_id

                    item['hashid']              = self.get_hash(str_hash)
                    item['timeOrderDiscovered'] = time.time()
                    item['timeTradeOpened']     = None
                    item['timeTradeClosed']     = None
                    item['timeTradeAttempedOpened'] = None
                    item['symbol']      = symbolRaw
                    item['action']      = actionRaw
                    item['lots']        = 1 #TODO fix this
                    item['openPrice']   = float(openPriceRaw)
                    item['closePrice']  = None
                    item['url']         = response.url
                    item['profit']      = None
                    item['orderid']     = None
                    item['tradeid']     = None

                    self.logger.info('Position parsing completed')

                    yield item
                except:
                    self.logger.error('Exception parsing position')



