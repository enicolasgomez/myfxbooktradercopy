from twisted.internet import reactor
from scrapy.crawler import CrawlerRunner
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from twisted.internet.task import deferLater
import time
import logging

from persistentstore import PersistentStore 
import socketio
import fxcmpy
import json
import requests
from socketIO_client import SocketIO
from difflib import get_close_matches 

positions = {}
orderTradeMap = {}
symbols = []

logger = logging.getLogger()
logFormatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(funcName)s - line %(lineno)d")
#logging.getLogger('scrapy').setLevel(logging.ERROR)
logging.getLogger('scrapy').propagate = False
logging.getLogger('FXCM').setLevel(logging.WARNING)
#logging.getLogger('scrapy.statscollectors').setLevel(logging.WARNING)
# Set up the console handler
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

# Set up the file handler 
fileHandler = logging.FileHandler("{0}/{1}.log".format("./", "main"))
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)


TOKEN = ''
con = fxcmpy.fxcmpy(access_token = TOKEN, log_level = 'error')
symbols = con.get_instruments()

def match_trade_order_data(data):
    if 'tradeId' in data:
      orderTradeMap[str(data['orderId'])] = str(data['tradeId'])

con.subscribe_data_model('Order', (match_trade_order_data,))

#https://doc.scrapy.org/en/latest/topics/practices.html#running-multiple-spiders-in-the-same-process
def sleep(self, *args, seconds):
    """Non blocking sleep callback"""
    return deferLater(reactor, seconds, lambda: None)

def crash(failure):
    print('oops, spider crashed')
    logging.error(failure.getTraceback())

def _crawl(result):
    deferred = process.crawl('rofxnet', domain='rofxnet')
    persistentstore = PersistentStore()

    logging.info('Persistent store...')
    persistentstore.log(logging)

    logging.info('Parsing items...')

    try:
        to_be_opened = persistentstore.to_be_opened_items()
        to_be_closed = persistentstore.to_be_closed_items()

        logging.info('To be opened: ' + str(len(to_be_opened)))
        logging.info('To be closed: ' + str(len(to_be_closed)))

        for k,v in orderTradeMap.items():
            persistentstore.tag_trade_id(k, v)

        for key, item in to_be_opened.items():
            symbol = get_close_matches(item['symbol'], symbols) # EURUSD > EUR/USD
            symbol = next(iter(symbol), None)
            if symbol:
                is_buy = (item['action'].upper() == 'BUY')
                lots = item['lots']
                order = con.open_trade(symbol=symbol, is_buy=is_buy,
                                rate=0, is_in_pips=False,
                                amount=lots, time_in_force='GTC',
                                order_type='AtMarket')
                if order != 0 :
                    persistentstore.tag_opened(key, str(order.__orderId__), time.time())
                    logging.info('New order opened: ' + key) 
                    persistentstore.tag_opened(key, str(order.__orderId__), time.time())
                    
                if order is None: #returns None when instantly opened? grab from trades table
                    fake_order_id = int(time.time())
                    persistentstore.tag_attemped_opened(key, fake_order_id)
                    logging.info('Server returned None instead of Order but order was opened') 
                    logging.info('Attemping manual grep from trades table.')
                    trades = con.get_open_positions()
                    trades = trades.loc[(trades['currency'] == symbol) & (trades['isBuy'] == is_buy)].sort_values(by=['time']) #get open trades for given parameters
                    for index, trade in trades.iterrows():
                        trade_id = trade['tradeId']
                        existing = persistentstore.get_item_by_trade_id(trade_id) #might be opened already?
                        if existing is None:
                            persistentstore.tag_opened(key, str(fake_order_id), time.time())
                            orderTradeMap[str(fake_order_id)] = str(trade_id)
                            persistentstore.tag_trade_id(fake_order_id, trade_id)
                            break

        for hashid in to_be_closed:
            item = persistentstore.get_item_by_id(hashid)
            lots = item['lots']
            con.close_trade(trade_id=item['tradeid'], amount=lots)
            profit = 0 #TODO
            persistentstore.tag_closed(hashid, profit, time.time())
            logging.info('Position closed: ' + hashid)
    except:
        logging.error('Exception parsing item')

    persistentstore.clear_parsed_items()
    persistentstore.dump()

    deferred.addCallback(lambda results: logging.info('waiting 60 seconds before restart...'))
    deferred.addCallback(sleep, seconds=60)
    deferred.addCallback(_crawl)
    deferred.addErrback(crash)  # <-- add errback here
    return deferred

process = CrawlerProcess(get_project_settings())
_crawl(None)
process.start()

