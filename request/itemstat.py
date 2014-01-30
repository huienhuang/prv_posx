import json
import os
import time
import config
import re
import datetime

DEFAULT_PERM = 1 << config.USER_PERM_BIT['item stat access']
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('itemstat.html')

    specific_vends = {} #{'pat': {'sol pak': True}}
    def fn_stat(self):
        item_id = self.qsv_int('item_id')
        frm_date = self.qsv_int('from_date')
        
        if not item_id or not frm_date: return
        
        db = self.db()
        cur = db.cur()
        
        sv = self.specific_vends.get(self.user_name.lower())
        if sv != None:
            cur.execute('select detail from sync_items where sid=%d' % item_id)
            row = cur.fetchall()
            if not row: return
            detail = json.loads(row[0][0])
            allowed = None
            for vend in detail['vends']:
                allowed = sv.get(vend[0].lower())
                if allowed == None: continue
                if not allowed: return
                break
            if allowed == None and not sv.get(0, False): return
        
        cur.execute('select r.sid,r.sid_type,r.type,r.creation_date,h.qtydiff from sync_items_hist h left join sync_receipts r on (h.docsid=r.sid and h.sid_type=r.sid_type) where h.itemsid=%d and r.creation_date>=%d and r.creation_date<=%d and (h.flag>>8)<=1' % (
            item_id, frm_date, time.time()
            )
        )
        stat = {}
        for r in cur.fetchall():
            lt = time.localtime(int(r[3]))
            
            k = '%04d-%02d' % (lt.tm_year, lt.tm_mon)
            s = stat.get(k)
            if not s: s = stat[k] = {'qty': [0, 0], 'count':[0, 0]}
            
            sid_type = int(r[1])
            s['qty'][sid_type] += float(r[4])
            s['count'][sid_type] += 1
            
        t = stat.keys()
        t.sort()
        stat = [ (i, stat[i]) for i in t ]
        
        self.req.writejs({'item_id':str(item_id), 'stat':stat})

