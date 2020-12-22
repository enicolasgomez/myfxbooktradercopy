import shelve

class SingletonMeta(type):
    """
    The Singleton class can be implemented in different ways in Python. Some
    possible methods include: base class, decorator, metaclass. We will use the
    metaclass because it is best suited for this purpose.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """`
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls] 

class PersistentStore(metaclass=SingletonMeta):
    db_name = 'positions.db'
    db_name_dump = 'positions.dump.db'
    parsed_items = {}
    inited = False 

    def set_inited(self):
        if not self.inited:
            self.inited = True

    def log(self, logger):
        logger.info(self.parsed_items)

    def add_parsed_item(self, item):
        s = shelve.open(self.db_name)
        self.parsed_items[item['hashid']] = item
        if item['hashid'] not in s:
            self.add_stored_item(item)  

    def clear_parsed_items(self):
        self.parsed_items.clear()

    def add_stored_item(self, item):
        s = shelve.open(self.db_name)
        try:
            s[item['hashid']] = item 
        finally:
            s.close()

    #any item which has not a tradeOpened 
    def to_be_opened_items(self):
        s = shelve.open(self.db_name)
        #self.debug(s.items())
        to_be_opened = { key: item for (key, item) in s.items() if item['timeTradeOpened'] is None }
        return to_be_opened

    #any item which has a tradeOpened and itemid but not a tradeClosed date
    def opened_items(self):
        s = shelve.open(self.db_name)
        opened = { key: item for (key, item) in s.items()
                    if item['timeTradeOpened'] is not None 
                    and item['timeTradeClosed'] is None 
                    and item['tradeid'] is not None }
        return opened

    def get_orphaned_order_by_params(self, symbol, is_buy):
        s = shelve.open(self.db_name)
        target_action = "BUY" if is_buy else "SELL"
        key = [ key for (key, item) in s.items() if item['symbol'] == symbol 
                                                and item['action'].upper() == target_action 
                                                and item['timeTradeAttempedOpened'] == -1 ]
        return key

    def tag_attemped_opened(self, hashid, timeopened):
        s = shelve.open(self.db_name)
        try:
            tmp = s[hashid]
            tmp['timeTradeAttempedOpened'] = timeopened
            s[hashid] = tmp
        finally:
            s.close()

    def tag_opened(self, hashid, orderid, timeopened):
        s = shelve.open(self.db_name)
        try:
            tmp = s[hashid]
            tmp['orderid'] = orderid
            tmp['timeTradeOpened'] = timeopened
            s[hashid] = tmp
        finally:
            s.close()

    def tag_closed(self, hashid, profit, timeclosed):
        s = shelve.open(self.db_name)
        try:
            tmp = s[hashid]
            tmp['profit'] = profit
            tmp['timeTradeClosed'] = timeclosed
            s[hashid] = tmp
        finally:
            s.close()

    def get_item_by_id(self, hashid):
        s = shelve.open(self.db_name)
        key = [ key for (key, item) in s.items() if str(item['hashid']) == str(hashid) ]
        r = None 
        if len(key) > 0 :
            r = s[key[0]]
        s.close()
        return r

    def get_item_by_trade_id(self, tradeid):
        s = shelve.open(self.db_name)
        key = [ key for (key, item) in s.items() if str(item['tradeid']) == str(tradeid) ]
        r = None 
        if len(key) > 0 :
            r = s[key[0]]
        s.close()
        return r

    def tag_trade_id(self, orderid, tradeid):
        s = shelve.open(self.db_name)
        try:
            key = [ key for (key, item) in s.items() if str(item['orderid']) == str(orderid) and item['tradeid'] is None ]
            if len(key) > 0 :
                key = key[0]
                tmp = s[key]
                tmp['tradeid'] = tradeid
                s[key] = tmp
        finally:
            s.close()

    #any item which is opened but is not listed in the recently current iteration for parsed_items
    def to_be_closed_items(self):
        opened = self.opened_items()
        to_be_closed = []
        #if not in recently parsed items, then needs closing
        if self.inited:
            for item in opened:
                if item not in self.parsed_items:
                    to_be_closed.append(item)
        return to_be_closed

    #do maintainance for items which have been opened and closed
    def dump(self):
        s = shelve.open(self.db_name)
        dump = shelve.open(self.db_name_dump)
        try:
            to_be_dumped = { key: item for (key, item) in s.items()
                            if item['timeTradeOpened'] is not None 
                            and item['timeTradeClosed'] is not None }

            for key in to_be_dumped:
                if key not in dump:
                    dump[key] = s[key]
                del s[key]

        finally:
            s.close()
            dump.close()