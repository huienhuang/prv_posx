import config
import hashlib
import json
import time
import struct
import socket
import re


DEFAULT_PERM = 0x00000000
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    regx_kw = re.compile(u'[^ 0-9a-z,]+', re.I|re.M|re.S)
    def fn_itemsearch(self):
        kw = self.qsv_str('term')
        if not kw: return
        mode = self.qsv_int('mode')
        
        kws = set(self.regx_kw.sub(u' ', kw).strip().lower().replace(u',', u' ').strip().split(u' '))
        kws.discard(u'')
        if not kws: return
        
        db = self.db()
        cur = db.cur()
        
        sid_lku = {}
        items = []
        if kw.isdigit():
            cur.execute('select i.sid,i.num,i.name,i.detail,u.default_uom_idx from sync_items_upcs u left join sync_items i on (u.sid=i.sid) where u.upc=%d order by i.num asc limit 10' % (int(kw),))
            for x in cur.fetchall():
                sid_lku[ x[0] ] = True
                items.append( [str(x[0]),] + x[1:] )
        
        if mode:
            kw = '+' + u' +'.join([k for k in kws])
        else:
            kw = '+' + u' +'.join([k + '* ' + k for k in kws])
        qs = "select sid,num,name,detail,(match(lookup,name) against (%s in boolean mode) + match(lookup) against (%s in boolean mode)*2) as pos from sync_items where match(lookup,name) against (%s in boolean mode) order by pos desc,num asc limit 10"
        cur.execute(qs, (kw, kw.replace(u'+', u''), kw))
        k = min(len(items), 2)
        for x in cur.fetchall():
            if sid_lku.has_key(x[0]): continue
            items.append( [str(x[0]),] + list(x[1:4]) + [None] )
            k += 1
            if k >= 10: break
        
        for t in items:
            js = t[3] = json.loads(t[3])
            for u in js['units']: u[0] = None
            del js['udfs']
        
        self.req.writejs(items)
        
    def fn_alu(self):
        self.req.writefile('itemalu.html')

