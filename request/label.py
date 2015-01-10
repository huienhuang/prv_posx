import config
import hashlib
import json
import time
import struct
import socket
import re


TEMPLATES = (
('5163', 'Large', 1),
('5163001', 'Large - All ALU', 1),

('5160', 'Small', 0),
('5160001', 'Small - All ALU', 0),

('5960202', u"Arrow" + ' 30x', None),

('5163301', 'large - Warehouse', 2),

('5160009', 'Small - Repeat', None),
                
('5960200', u"\u5305\u88C5\u76D2\u6807\u7B7E" + ' 30x', None),
('5163200', u"\u5305\u88C5\u76D2\u6807\u7B7E" + ' 10x', None),
('5960201', u"NowPak Logo" + ' 30x', None),
('5960204', u"Forest Logo" + ' 30x', None),
('5960203', u"Forest ADDR" + ' 30x', None),
)

TEMPLATES_D = dict([(f_v[0], f_v[1:])for f_v in TEMPLATES])


DEFAULT_PERM = (1 << config.USER_PERM_BIT['base access']) | (1 << config.USER_PERM_BIT['normal access'])
class RequestHandler(App.load('/request/sync').RequestHandler):
    
    def fn_default(self):
        d = {
            'templates': TEMPLATES
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
        
        
    def fn_auto(self):
        l_type = self.req.psv_int('type')

        idx = TEMPLATES_D.get( self.req.psv_ustr('tmpl'), [None, None] )[1]
        if idx == None: return
        
        cur = self.cur()
        if l_type == 1:
            cur.execute('select sid,num,name,detail from sync_items where sid in (select sid from item where inv_flag&%d=%d order by sid) order by sid asc limit 100' % (1 << idx, 1 << idx))
            ret = []
            for r in cur.fetchall():
                r = list(r)
                r[0] = str(r[0])
                r[3] = json.loads(r[3])
                
                js = r[3]
                for u in js['units']: u[0] = u[0][:1]
                del js['udfs']
                
                ret.append(r)
                
            self.req.writejs({'type': 1, 'lst': ret})
                
        elif l_type == 2:
            sids = map(str, map(int, self.req.psv_ustr('data').split('|')))
            if not sids: return
            
            cur.execute('update item set inv_flag=inv_flag&%d where sid in (%s)' % (
                ~(1 << idx), ','.join(sids),
                )
            )
            self.req.writejs({'err': 0})
        
        elif l_type == 3:
            
            cur.execute('update item set inv_flag=inv_flag&%d' % (
                ~(1 << idx),
                )
            )
            self.req.writejs({'err': 0})
        
        
        