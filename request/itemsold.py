import json
import os
import time
import config
import re
import datetime
import tools
import csv
import cStringIO

DEFAULT_PERM = 1 << config.USER_PERM_BIT['item stat access']
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        cur = self.cur()
        cur.execute('select id,nz from report where type=1 order by id desc')
        profiles = cur.fetchall()
        r = {
            'profiles': profiles
        }
        self.req.writefile('items_sold_report.html', r)

    def get_items_sold_report(self, tids, frm_ts, to_ts, imm):
        cur = self.cur()
        cur.execute('select h.itemsid,r.order_date,h.qtydiff from sync_items_hist h left join sync_receipts r on (h.docsid=r.sid and h.sid_type=r.sid_type) where h.itemsid in (%s) and r.order_date>=%d and r.order_date<%d and (h.flag>>8)<=1' % (
            ','.join(map(str, tids)), frm_ts, to_ts
            )
        )
        stat = {}
        for r in cur.fetchall():
            lt = time.localtime(int(r[1]))
            year,month = tools.get_date_lower(lt.tm_year, lt.tm_mon, imm)
            
            k = '%04d-%02d' % (year, month)
            stat.setdefault(r[0], {}).setdefault(k, [0])[0] += -r[2]
            
        return stat

    def fn_get_items_sold_report(self):
        tids_lst = map(int, self.req.psv_ustr('tids').split(','))
        tids = set(tids_lst)
        if not tids or len(tids) != len(tids_lst): return
        frm_ts = self.req.psv_int('frm_ts')
        to_ts = self.req.psv_int('to_ts')
        imm = self.req.psv_int('interval')
        if not frm_ts or not to_ts: return
        
        stat = self.get_items_sold_report(tids, frm_ts, to_ts, imm)
        self.req.writejs({'stat':stat})
    
    def fn_save_profile(self):
        js = self.req.psv_js('js')
        
        items = []
        tids = set()
        for item in js['items']:
            tid, uom_idx = map(int, item)
            items.append( [tid, uom_idx] )
            tids.add(tid)
        if len(tids) != len(items): return
        
        pid = int(js['pid'])
        nz = js['nz'][:128].strip()
        js = {
            'frm_ts': int(js['frm_ts']),
            'to_ts': int(js['to_ts']),
            'interval': int(js['interval']),
            'items': items,
        }
        
        cur = self.cur()
        js_s = json.dumps(js, separators=(',',':'))
        if pid:
            cur.execute('update report set js=%s where id=%s and type=1', (
                js_s, pid
                )
            )
        else:
            cur.execute('insert into report values (null,1,%s,%s)', (
                nz, js_s
                )
            )
            pid = cur.lastrowid
        
        self.req.writejs( {'pid': pid} )

    def fn_delete_profile(self):
        pid = self.req.psv_int('pid')
        if not pid: return
        
        cur = self.cur()
        cur.execute('delete from report where id=%s and type=1', (pid,))
        self.req.writejs({'ret': int(bool(cur.rowcount > 0))})
        
    def fn_load_profile(self):
        pid = self.req.qsv_int('pid')
        if not pid: return
        
        cur = self.cur()
        cur.execute('select js from report where id=%s and type=1', (pid,))
        rows = cur.fetchall()
        if not rows: return;
        
        js = json.loads(rows[0][0])
        js['pid'] = pid
        
        items = []
        o_items = js['items']
        if o_items:
            lku = {}
            cur.execute('select sid,num,name,detail from sync_items where sid in (%s)' % ','.join([str(x[0]) for x in o_items]))
            for r in cur.fetchall(): lku[ r[0] ] = r
            
            for tid,uom_idx in o_items:
                r = lku.get(tid)
                if not r: continue
                r = list(r)
                r[0] = str(r[0])
                r[3] = json.loads(r[3])
                items.append( [r, uom_idx] )
            
        js['items'] = items
        
        self.req.writejs(js)
        
    def fn_export_csv(self):
        js = self.req.psv_js('js')
        
        items = []
        tids = set()
        for item in js['items']:
            tid, uom_idx = map(int, item)
            items.append( [tid, uom_idx] )
            tids.add(tid)
        if not tids or len(tids) != len(items): return
        
        frm_ts = int(js['frm_ts'])
        to_ts = int(js['to_ts'])
        imm = int(js['interval'])
        if not frm_ts or not to_ts or imm < 1: return
        
        stat = self.get_items_sold_report(tids, frm_ts, to_ts, imm)
        frm_tp = time.localtime(frm_ts)
        to_tp = time.localtime(to_ts)
        
        s = frm_tp.tm_year * 12 + frm_tp.tm_mon - 1
        e = to_tp.tm_year * 12 + to_tp.tm_mon - 1
        
        data = []
        hdr = ['#', 'ALU', 'Name', 'OH', 'PC']
        i = s
        while(i < e):
            yr, mon = divmod(i, 12)
            mon += 1
            i += imm
            hdr.append('%04d-%02d' % (yr, mon))
        hdr.append('AVG')
        hdr.append('Total')
        data.append(hdr)
        
        cur = self.cur()
        for tid,uom_idx in items:
            cur.execute('select num,name,detail from sync_items where sid=%s', (tid,))
            rows = cur.fetchall()
            if not rows: continue
            
            num,name,detail = rows[0]
            detail = json.loads(detail)
            units = detail['units']
            qtys = detail['qty']
            uom = units[uom_idx]
            mul = uom[3]
            if not mul: continue
            
            OH = qtys[0] / mul
            PC = qtys[3] / mul
            row = [
                str(num),
                (units[0][1] or '').encode('utf8'),
                (name or '').encode('utf8'),
                '%0.1f' % (OH,),
                '%0.1f' % (PC,)
            ]
            
            a = stat.get(tid, {})
            total = 0
            count = 0
            i = s
            while(i < e):
                yr, mon = divmod(i, 12)
                mon += 1
                i += imm
                
                count += 1
                t = a.get('%04d-%02d' % (yr, mon))
                if t:
                    t[0] /= mul
                    total += t[0]
                row.append( t and '%0.1f' % (t[0],) or '' )
            
            row.append( count and '%0.1f' % (total / count,) or '' )
            row.append( '%0.1f' % (total,) )
            data.append(row)
            
        fp = cStringIO.StringIO()
        wt = csv.writer(fp)
        for r in data: wt.writerow(r)
        
        
        self.req.out_headers['content-type'] = 'application/octet-stream'
        self.req.out_headers['content-disposition'] = 'attachment; filename="data.csv"'
        self.req.write( fp.getvalue() )
        

    def fn_make_po(self):
        js = self.req.psv_js('js')

        