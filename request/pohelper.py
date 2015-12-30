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
    'id': 'POHELPER_C1000001',
    'name': 'Po Helper',
    'perm_list': [
    ('access', ''),
    ('admin', ''),
    ]
}

PERM_ADMIN = 1 << 1

class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        js = self.get_data_file_cached('items_vendors', 'items_vendors.txt') or {}

        users = self.getuserlist()
        users_lku = dict([x[:2] for x in users])

        cur = self.cur()
        cur.execute("select pid,pdesc,flg,uid from inv_request where dtype=2 and (uid=%s or (flg&2)!=0) order by pid desc limit 30", (
            self.user_id,
            )
        )
        po_lst = cur.fetchall()

        r = {
            'profiles': sorted(js.items(), key=lambda f_x:f_x[1][0].lower()),
            'po_lst': po_lst,
            'users_lku': users_lku
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
    
    def fn_publish(self):
        pid = self.req.qsv_int('pid')
        if not pid: return

        cur = self.cur()
        cur.execute('update inv_request set rev=rev+1,flg=flg|2 where dtype=2 and pid=%s and uid=%s and (flg&3)=0', (
            pid, self.user_id, 
            )
        )
        self.req.writejs({'err': int(cur.rowcount<=0)})

    fn_publish.PERM = PERM_ADMIN

    def fn_save_profile(self):
        js = self.req.psv_js('js')
        
        items = []
        tids = set()
        for item in js['items']:
            tid,num,uom_idx,req_qty = map(int, item)
            items.append( [tid,num,uom_idx,req_qty] )
            tids.add(tid)
        if len(tids) != len(items): return
        
        pid = int(js['pid'])
        nz = js['nz'][:128].strip()
        if js['ref']:
            ref = str(int(js['ref']))
        else:
            ref = None
        dst = 0
        js = {
            'frm_ts': int(js['frm_ts']),
            'to_ts': int(js['to_ts']),
            'interval': int(js['interval']),
            'items': items,
            'store_id': 0
        }
        
        cur = self.cur()
        js_s = json.dumps(js, separators=(',',':'))
        if pid:
            cur.execute('update inv_request set rev=rev+1,dst=%s,pjs=%s where pid=%s and (uid=%s or (flg&2)!=0) and dtype=2 and (flg&1)=0', (
                dst, js_s, pid, self.user_id,
                )
            )
        else:
            cur.execute('insert into inv_request values (null,1,%s,2,0,'+(ref == None and 'null' or ref)+',0,%s,%s,%s,%s)', (
                dst, int(time.time()), self.user_id, nz, js_s
                )
            )
            pid = cur.lastrowid
        
        self.req.writejs( {'pid': pid} )

    def fn_delete_profile(self):
        pid = self.req.psv_int('pid')
        if not pid: return
        
        cur = self.cur()
        cur.execute('delete from inv_request where pid=%s and (uid=%s or (flg&2)!=0) and dtype=2 and (flg&1)=0', (pid, self.user_id))
        self.req.writejs({'ret': int(bool(cur.rowcount > 0))})

    def fn_load_profile(self):
        pid = self.req.qsv_int('pid')
        if not pid: return
        pid_type = self.req.qsv_str('pid_type')

        mixed = False

        js = {}
        cur = self.cur()
        if pid_type == 'V':
            fjs = self.get_data_file_cached('items_vendors', 'items_vendors.txt')
            if not fjs: return
            vjs = [ [f_x, 0, 0, 0] for f_x in fjs[pid][1] ]
            pid_type = 0

        elif pid_type == 'P':
            cur.execute('select dst,ref,pjs from inv_request where pid=%s and dtype=2', (pid,))
            dst,ref,pjs = cur.fetchall()[0]
            js = json.loads(pjs)
            js['dst'] = dst
            vjs = js['items']
            if ref != None:
                lku = set([f_x[0] for f_x in vjs])
                for sid in self.get_data_file_cached('items_vendors', 'items_vendors.txt').get(ref, (None, []))[1]:
                    if sid in lku: continue
                    vjs.append( [sid, None, None, 0] )
                    mixed = True
            pid_type = 1

        else:
            return

        js['pid'] = str(pid)
        
        items = []
        msgs = []
        if vjs:
            lku = {}
            cur = self.cur()
            cur.execute('select sid,num,name,detail from sync_items where sid in (%s)' % ','.join([str(f_x[0]) for f_x in vjs]))
            for r in cur.fetchall(): lku[ r[0] ] = r
            
            for t in vjs:
                r = lku.get(t[0])
                if not r: continue
                r = list(r)
                r[0] = str(r[0])
                ijs = r[3] = json.loads(r[3])

                if pid_type == 0:
                    ijs['default_uom_idx'] = ijs['order_uom_idx']
                    ijs['req_qty'] = 0
                else:
                    if mixed and t[2] == None: t[2] = ijs['order_uom_idx']

                    if t[2] < len(ijs['units']):
                        ijs['default_uom_idx'] = t[2]
                        ijs['req_qty'] = t[3]
                    else:
                        msgs.append('%d - UOM OUT OF RANGE' % (r[1],))
                items.append(r)
            
            if mixed: items.sort(key=lambda f_x:f_x[1])

        js['items'] = items
        js['msgs'] = msgs
        
        self.req.writejs(js)
        

