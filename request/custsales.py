import json
import os
import time
import config
import re
import datetime
import tools
import csv
import cStringIO
import bisect


CFG = {
    'id': 'CUSTSALES_C0000006',
    'name': 'Customer Sales',
    'perm_list': [
    ('access', ''),
    ]
}

REPORT_TYPE = 8

class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        cur = self.cur()
        cur.execute('select id,nz from report where type='+str(REPORT_TYPE)+' order by id desc')
        profiles = cur.fetchall()
        r = {
            'profiles': profiles
        }
        self.req.writefile('customer_sales_report.html', r)

    def get_customer_sales_report(self, cids, frm_ts, to_ts, imm):
        rjs = (self.get_data_file_cached('receipt_report', 'receipt_report.txt') or {}).get('customer', {})

        d_stat = {}
        for cid in cids:
            cust = rjs.get(cid)
            if not cust: continue
            stat = d_stat.setdefault(cid, {})

            l_dt = [ f_x[0] for f_x in cust ]
            for ds in cust[ bisect.bisect_left(l_dt, frm_ts): bisect.bisect_left(l_dt, to_ts) ]:
                lt = time.localtime(ds[0])
                year,month = tools.get_date_lower(lt.tm_year, lt.tm_mon, imm)

                k = '%04d-%02d' % (year, month)
                stat.setdefault(k, [0])[0] += ds[1][0]
            
        return d_stat

    def fn_get_customer_sales_report(self):
        tids_lst = map(int, self.req.psv_ustr('tids').split(','))
        tids = set(tids_lst)
        if not tids or len(tids) != len(tids_lst): return
        frm_ts = self.req.psv_int('frm_ts')
        to_ts = self.req.psv_int('to_ts')
        imm = self.req.psv_int('interval')
        if not frm_ts or not to_ts: return
        
        stat = self.get_customer_sales_report(tids, frm_ts, to_ts, imm)
        self.req.writejs({'stat':stat})
    
    def fn_save_profile(self):
        js = self.req.psv_js('js')
        
        cids = map(int, js['cids'])
        if len(cids) != len(set(cids)): return
        
        pid = int(js['pid'])
        nz = js['nz'][:128].strip()
        js = {
            'frm_ts': int(js['frm_ts']),
            'to_ts': int(js['to_ts']),
            'interval': int(js['interval']),
            'cids': cids,
        }
        
        cur = self.cur()
        js_s = json.dumps(js, separators=(',',':'))
        if pid:
            cur.execute('update report set js=%s where id=%s and type=%s', (
                js_s, pid, REPORT_TYPE
                )
            )
        else:
            cur.execute('insert into report values (null,%s,%s,%s)', (
                REPORT_TYPE, nz, js_s
                )
            )
            pid = cur.lastrowid
        
        self.req.writejs( {'pid': pid} )

    def fn_delete_profile(self):
        pid = self.req.psv_int('pid')
        if not pid: return
        
        cur = self.cur()
        cur.execute('delete from report where id=%s and type=%s', (pid, REPORT_TYPE))
        self.req.writejs({'ret': int(bool(cur.rowcount > 0))})
        
    def fn_load_profile(self):
        pid = self.req.qsv_int('pid')
        if not pid: return
        
        cur = self.cur()
        cur.execute('select js from report where id=%s and type=%s', (pid, REPORT_TYPE))
        rows = cur.fetchall()
        if not rows: return;
        
        js = json.loads(rows[0][0])
        js['pid'] = pid
        
        custs = []
        cids = js['cids']
        if cids:
            lku = {}
            cur.execute('select sid,name,detail from sync_customers where sid in (%s)' % ','.join( map(str, cids) ))
            for r in cur.fetchall(): lku[ r[0] ] = r
            
            for cid in cids:
                r = lku.get(cid)
                if not r: continue
                r = list(r)
                r[0] = str(r[0])
                r[2] = json.loads(r[2])
                custs.append(r)
            
        js['custs'] = custs
        
        self.req.writejs(js)
        
    def fn_export_csv(self):
        js = self.req.psv_js('js')
        
        cids = map(int, js['cids'])
        if len(cids) != len(set(cids)): return
        
        frm_ts = int(js['frm_ts'])
        to_ts = int(js['to_ts'])
        imm = int(js['interval'])
        if not frm_ts or not to_ts or imm < 1: return
        
        stat = self.get_customer_sales_report(cids, frm_ts, to_ts, imm)
        frm_tp = time.localtime(frm_ts)
        to_tp = time.localtime(to_ts)
        
        s = frm_tp.tm_year * 12 + frm_tp.tm_mon - 1
        e = to_tp.tm_year * 12 + to_tp.tm_mon - 1
        
        data = []
        hdr = ['Name']
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
        for cid in cids:
            cur.execute('select name from sync_customers where sid=%s', (cid,))
            rows = cur.fetchall()
            if not rows: continue
            
            name = rows[0][0]
            row = [
                (name or '').encode('utf8'),
            ]
            
            a = stat.get(cid, {})
            total = 0
            count = 0
            i = s
            while(i < e):
                yr, mon = divmod(i, 12)
                mon += 1
                i += imm
                
                count += 1
                t = a.get('%04d-%02d' % (yr, mon))
                if t: total += t[0]
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
        
