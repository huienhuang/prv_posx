import json
import time
import datetime
import config


DEFAULT_PERM = (1 << config.USER_PERM_BIT['base access']) | (1 << config.USER_PERM_BIT['normal access'])
class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('mhome.html')
    
    def fn_search_item(self):
        kw = self.qsv_str('term')
        if not kw: return
        mode = self.qsv_int('mode')
        mini = self.qsv_int('mini')
        self.req.writejs( self.search_item(kw, mode, mini and 4 or 10) )

    def fn_get_item(self):
    	sid = self.qsv_int('sid')
    	self.req.writejs( {'item': self.get_item_by_sid(sid)} )

