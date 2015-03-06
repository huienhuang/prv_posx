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

DEFAULT_PERM = 1 << config.USER_PERM_BIT['item stat access']
ADV_PERM = (1 << config.USER_PERM_BIT['purchasing']) | (1 << config.USER_PERM_BIT['item stat access'])
class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        js = self.get_data_file_cached('items_vendors', 'items_vendors.txt')
        if not js: return

        cur = self.cur()
        cur.execute("select pid,ref,pdesc from inv_request order by pid desc limit 30")
        po_lst = cur.fetchall()

        r = {
            'profiles': sorted(js.items(), key=lambda f_x:f_x[1][0].lower()),
            'po_lst': po_lst
        }
        self.req.writefile('pohelper.html', r)

    def get_items_sold_report(self, tids, frm_ts, to_ts, imm):
        items = self.get_items_stat()

        dt = time.localtime(frm_ts)
        frm_mon = dt.tm_year * 100 + dt.tm_mon
        dt = time.localtime(to_ts)
        to_mon = dt.tm_year * 100 + dt.tm_mon

        stat = {}
        for sid in tids:
            item = items.get(sid, (None, None, []))[2]
            mon_lst = [ f_x[0] for f_x in item ]
            for i in range( bisect.bisect_left(mon_lst, frm_mon),  bisect.bisect_left(mon_lst, to_mon) ):
                r = item[i]
                year,month = divmod(r[0], 100)
                year,month = tools.get_date_lower(year, month, imm)
            
                k = '%04d-%02d' % (year, month)
                stat.setdefault(sid, {}).setdefault(k, [0])[0] += r[1]

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

    fn_save_profile.PERM = ADV_PERM

    def fn_delete_profile(self):
        pid = self.req.psv_int('pid')
        if not pid: return
        
        cur = self.cur()
        cur.execute('delete from report where id=%s and type=1', (pid,))
        self.req.writejs({'ret': int(bool(cur.rowcount > 0))})
        
    fn_delete_profile.PERM = ADV_PERM

    def fn_load_profile(self):
        pid = self.req.qsv_int('pid')
        if not pid: return

        vjs = self.get_data_file_cached('items_vendors', 'items_vendors.txt')
        if not vjs: return
        
        vendor = vjs[pid]
        
        js = {}
        js['pid'] = str(pid)
        
        items = []
        o_items = vendor[1]
        if o_items:
            lku = {}
            cur = self.cur()
            cur.execute('select sid,num,name,detail from sync_items where sid in (%s)' % ','.join([str(x) for x in o_items]))
            for r in cur.fetchall(): lku[ r[0] ] = r
            
            for tid in o_items:
                r = lku.get(tid)
                if not r: continue
                r = list(r)
                r[0] = str(r[0])
                r[3] = json.loads(r[3])
                items.append( (r, r[3]['order_uom_idx']) )
            
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
        

    fn_export_csv.PERM = ADV_PERM

    def fn_make_po(self):
        js = self.req.psv_js('js')
        ref = int(js['ref'])
        lst = [ map(int, f_x[:4]) for f_x in js['lst'] if int(f_x[3]) > 0 ]
        if not lst: return

        cur = self.cur()

        nz = ''
        cur.execute('select nz from report where type=1 and id=%s', (ref,))
        rows = cur.fetchall()
        if rows: nz = rows[0][0]

        cur.execute('insert into inv_request values(null,1,0,2,0,%s,0,%s,%s,%s,%s)', (
            ref, int(time.time()), int(self.user_id), nz, json.dumps(lst, separators=(',',':'))
            )
        )

        self.req.writejs( {'pid': cur.lastrowid} )


    def fn_save_po(self):
        js = self.req.psv_js('js')
        ref = int(js['ref'])
        lst = [ map(int, f_x[:4]) for f_x in js['lst'] if int(f_x[3]) > 0 ]
        if not lst: return

        cur = self.cur()
        cur.execute('insert into inv_request values(null,1,0,2,0,%s,0,%s,%s,%s,%s)', (
            ref, int(time.time()), int(self.user_id), nz, json.dumps(lst, separators=(',',':'))
            )
        )

        self.req.writejs( {'pid': cur.lastrowid} )

