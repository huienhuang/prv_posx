import config
import json
import re
import cStringIO
import csv
import time
import datetime

DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('advsrch_custs_items.html')
    
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
        
        
    def fn_export(self):
        data = self.req.psv_js('js')
        
        cids = map(int, data['cids'])
        if not cids: return
        
        sids = map(int, data['sids'])
        if not sids: return
        
        from_month = map(int, data['from_month'].split('-')[:2])
        from_month = int(time.mktime( datetime.date(from_month[0], from_month[1], 1).timetuple() ))
        
        to_month = map(int, data['to_month'].split('-')[:2])
        if to_month[1] < 12:
            to_month = [ to_month[0], to_month[1] + 1 ]
        else:
            to_month = [ to_month[0] + 1, 1 ]
        to_month = int(time.mktime( datetime.date(to_month[0], to_month[1], 1).timetuple() ))
        
        cur =self.cur()
        cur.execute('select h.itemsid,sum(h.qtydiff) from sync_receipts r left join sync_items_hist h on (r.sid=h.docsid and r.sid_type=h.sid_type and (h.flag>>8)<2) where r.cid in (%s) and h.itemsid in (%s) and r.order_date>=%s and r.order_date<%s group by h.itemsid' % (
            ','.join(map(str, cids)),
            ','.join(map(str, sids)),
            
            from_month, to_month
            )
        )
        items = dict(cur.fetchall())
        if not items: return
        
        lst = []
        cur.execute('select ri.num,ri.name,i.detail,ri.sid from sync_receipts_items ri left join sync_items i on (ri.sid=i.sid) where ri.sid in (%s)' % (
            ','.join(map(str, items.keys()))
            )
        )
        for r in cur.fetchall():
            qty = -items[r[3]]
            us = '%0.1f%s' % (qty, '')
            if r[2]:
                jsd = json.loads(r[2])
                unit = jsd['units'][ jsd['default_uom_idx'] ]
                if unit[3]:
                    us = '%0.1f%s' % (qty / unit[3], unit[2])
                else:
                    us = '%0.1f%s' % (qty, jsd['units'][0][2])
                    
            lst.append( (str(r[0]), r[1], us) )
        
        fp = cStringIO.StringIO()
        wt = csv.writer(fp)
        for r in lst: wt.writerow(r)
        
        self.req.out_headers['content-type'] = 'application/octet-stream'
        self.req.out_headers['content-disposition'] = 'attachment; filename="data.csv"'
        self.req.write( fp.getvalue() )
        
        
        
    