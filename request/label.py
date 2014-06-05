import config
import hashlib
import json
import time
import struct
import socket
import re


DEFAULT_PERM = (1 << config.USER_PERM_BIT['base access']) | (1 << config.USER_PERM_BIT['normal access'])
class RequestHandler(App.load('/request/sync').RequestHandler):
    
    def fn_default(self):
        d = {
            'templates': (
                ('5163', '5163 2 x 4 - large'),
                ('5160', '5960 1 x 2 5/8 - small'),
                ('5160009', '5960 1 x 2 5/8 - small - repeat'),
                
                ('5960200', u"\u5305\u88C5\u76D2\u6807\u7B7E" + ' 30x'),
                ('5163200', u"\u5305\u88C5\u76D2\u6807\u7B7E" + ' 10x'),
                ('5960201', u"NowPak Logo" + ' 30x'),
            )
        }
        self.req.writefile('label.html', d)


    def fn_preview(self):
        tmpl = self.req.qsv_int('tmpl')
        self.req.writefile('label/tmpl_%d.html' % (tmpl,))


    def fn_itemsearch(self):
        kw = self.qsv_str('term')
        if not kw: return
        mode = self.qsv_int('mode')
        
        items = self.search_item(kw, mode)
        for t in items:
            js = t[3] = json.loads(t[3])
            for u in js['units']: u[0] = u[0][:1]
            del js['udfs']
        
        self.req.writejs(items)
    
    
    def fn_get_item(self):
        row = self.get_item( self.qsv_int('item_no') )
        if not row: return
        
        js = row[3]
        for u in js['units']: u[0] = u[0][:1]
        del js['udfs']
        
        self.req.writejs(row)
        