import config
import json
import re
import cStringIO
import csv
import time
import datetime

CFG = {
    'id': 'ACCOUNT_MGR_AF888888',
    'name': 'ACCOUNT Manager',
    'perm_list': [
    ('access', ''),
    ]
}

PERM_ADMIN = 1 << 1

class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('account_mgr.html')
    
    regx_kw = re.compile(u'[^ 0-9a-z,]+', re.I|re.M|re.S)
    def fn_adv_item_srch(self):
        kw = self.qsv_str('term')
        if not kw: return
        mode = self.qsv_int('mode')
        
        cid = map(int, self.qsv_str('cids').split('|'))
        if not cid: return
        
        kws = set(self.regx_kw.sub(u' ', kw).strip().lower().replace(u',', u' ').strip().split(u' '))
        kws.discard(u'')
        if not kws: return
        
        db = self.db()
        cur = db.cur()
        
        cur.execute('select distinct h.itemsid from sync_receipts r left join sync_items_hist h on (r.sid=h.docsid and r.sid_type=h.sid_type and (h.flag>>8)<2) where r.cid in (%s) and h.itemsid is not null and h.itemsid != 1000000005' % (
            ','.join(map(str, cid)),
            )
        )
        sids = cur.fetchall()
        if not sids: return
        
        if mode:
            kw = '+' + u' +'.join([k for k in kws])
        else:
            kw = '+' + u' +'.join([k + '* ' + k for k in kws])
        qs = "select sid,num,name,detail,(match(lookup,name) against (%%s in boolean mode) + match(lookup) against (%%s in boolean mode)*2) as pos from sync_receipts_items where match(lookup,name) against (%%s in boolean mode) and sid in (%s) order by pos desc,num asc limit 100" % (','.join([str(x[0]) for x in sids]),)
        cur.execute(qs, (kw, kw.replace(u'+', u''), kw))
        
        res = [ [str(x[0]),] + list(x[1:]) for x in cur.fetchall() ]
        
        self.req.writejs(res)
