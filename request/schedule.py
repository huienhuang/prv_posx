import json
import time
import config
import datetime
import base64

MAX_DAYS = 7
ZONES = (
    ('*Other*', set([])),
    ('Downtown', set([ 0, 2 , 4])),
    ('Chinatown', set([ 0, 2, 4 ])),
    ('Fisherman', set([ 0, 2, 4 ])),
    ('GoldenGate', set([ 0, 2, 4 ])),
    ('Sunset', set([ 0, 2, 4 ])),
    ('Richmond', set([ 0, 2, 4 ])),
    ('Mission', set([ 0, 2, 4 ])),
    
    ('Eastbay', set([ 1, 3])),
    ('Southbay', set([ 1, 3])),
    ('Peninsula', set([ 1, 3])),
    
    ('NorthBay', set([ 1, 4])),
    
)
WDAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

SALES_PERM = 1 << config.USER_PERM_BIT['sales']
DELIVERY_MGR_PERM = 1 << config.USER_PERM_BIT['delivery_mgr']

DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        r = {
            'sales': [ f_user for f_user in self.getuserlist() if f_user[2] & SALES_PERM ],
            'zones': [ f_x[0] for f_x in ZONES ],
            'has_perm_delivery_mgr': DELIVERY_MGR_PERM
        }
        self.req.writefile('schedule.html', r)
    
    def fn_get_doc(self):
        d_num = self.req.qsv_ustr('num')
        if not d_num.isdigit(): return
        d_type = int(bool(self.req.qsv_int('type')))
        
        cur = self.cur()
        if d_type:
            cur.execute('select sid,num,assoc,order_date,global_js from sync_receipts where num=%s and sid_type=0 and (type&0xFF)=0 order by sid desc limit 1', (
                int(d_num),
                )
            )
        else:
            cur.execute('select sid,sonum,clerk,sodate,global_js from sync_salesorders where sonum=%s and (status>>4)=0 order by sid desc limit 1', (
                d_num,
                )
            )
        
        row = cur.fetchall()
        if not row: self.req.exitjs({'err': -1, 'err_s': 'document #%s not found' % (d_num,)})
        sid,num,assoc,doc_date,gjs = row[0]
        
        gjs = json.loads(gjs)
        company = (gjs.get('customer') or {}).get('company') or ''
        
        recs = []
        js = {
            'type': d_type,
            'num': num,
            'sid':str(sid),
            'assoc': assoc,
            'company': company,
            'total': gjs['total'],
            'recs': recs,
            'doc_date': time.strftime("%m/%d/%Y", time.localtime(doc_date))
        }
        
        cur.execute('select sc_id,sc_date,sc_rev,sc_flag,sc_prio,sc_note from schedule where doc_type=%s and doc_sid=%s order by sc_id asc', (
            d_type, sid
            )
        )
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            recs.append(r)
        
        self.req.writejs(js)
    
    def fn_set_doc(self):
        d_sid = self.req.psv_int('sid')
        
        d_date = map(int, self.req.psv_ustr('date').split('/'))
        d_date = datetime.date(d_date[2], d_date[0], d_date[1])
        if d_date < datetime.date.today(): self.req.exitjs({'err': -9, 'err_s': "Invalid Date"})
        d_date = d_date.year * 10000 + d_date.month * 100 + d_date.day
        
        d_type = int(bool(self.req.psv_int('type')))
        rev = self.req.psv_int('rev')
        prio = min(max(-1, self.req.psv_int('prio')), 2)
        sc_id = self.req.psv_int('sc_id')
        note = self.req.psv_ustr('note')[:128].strip()
        
        cts = int(time.time())
        
        cur = self.cur()
        if d_type:
            cur.execute('select num from sync_receipts where sid=%s and sid_type=0 and (type&0xFF)=0 order by sid desc limit 1', (
                d_sid,
                )
            )
        else:
            cur.execute('select sonum from sync_salesorders where sid=%s and (status>>4)=0 order by sid desc limit 1', (
                d_sid,
                )
            )
        
        row = cur.fetchall()
        if not row: return
        d_num = row[0][0]
        
        if sc_id == 0:
            cur.execute('insert into schedule values(null,%s,1,%s,%s,%s,%s,%s)', (
                d_date, 0, prio, d_type, d_sid, note
                )
            )
        else:
            cur.execute("select sc_date,sc_prio from schedule where sc_id=%s and sc_rev=%s", (
                sc_id, rev
                )
            )
            row = cur.fetchall()
            if not row: self.req.exitjs({'err': -3, 'err_s': "document #%s - record #%s - can't find the record" % (d_num, sc_id)})
            old_sc_date,old_sc_prio = row[0]
            if old_sc_date == d_date and old_sc_prio == prio: self.req.exitjs({'err': -2, 'err_s': "document #%s - record #%s - nothing changed" % (d_num, sc_id)})
            
            cur.execute("update schedule set sc_flag=sc_flag|%s,sc_rev=sc_rev+1,sc_date=%s,sc_prio=%s where sc_id=%s and sc_rev=%s and sc_flag&1=0", (
                old_sc_date != d_date and 2 or 0, d_date, prio, sc_id, rev
                )
            )
            
        rc = cur.rowcount
        if rc <= 0:
            self.req.exitjs({'err': -2, 'err_s': "document #%s - can't make any update" % (d_num, )})
        else:
            pass
            
        self.req.exitjs({'err': 0})
        
    
    def fn_accept_doc(self):
        sc_id = self.req.psv_int('sc_id')
        
        cur = self.cur();
        cur.execute('update schedule set sc_flag=sc_flag|1 where sc_id=%s and sc_flag&1=0', (sc_id,))
        err = int(cur.rowcount <= 0)
        if not err:
            pass
        
        self.req.writejs({'err': err})
    
    def fn_set_zone_state(self):
        date = self.req.psv_int('date')
        zidx = self.req.psv_int('zidx')
        state = self.req.psv_int('state')
        if zidx < 0 or zidx >= len(ZONES) or state not in (0, -1, 1): return
        
        m,d = divmod(date, 100)
        y,m = divmod(m, 100)
        dto = datetime.date(y, m, d)
        if dto < datetime.date.today(): self.req.exitjs({'err': -9, 'err_s': "Invalid Date"})
        
        cur = self.cur()
        cur.execute('insert into schedule_special values(%s,%s,%s) on duplicate key update ss_val=%s', (
            date, zidx, state, state
            )
        )
        err = int(cur.rowcount <= 0)
        if not err:
            pass
        
        self.req.writejs({'err': err})
        
    
    def fn_get_overview(self):
        clerk_id = self.qsv_int('clerk_id')
        
        odt = datetime.date.today()
        cdt = odt.year * 10000 + odt.month * 100 + odt.day
        
        d_ss = {}
        cur = self.cur()
        cur.execute('select ss_date,ss_zidx,ss_val from schedule_special where ss_date>=%s', (cdt,))
        for r in cur.fetchall(): d_ss[ (r[0] << 26) | r[1] ] = r[2]
        
        d_dt = {}
        for r in self.get_docs(cdt, -1, clerk_id, 1):
            zid = r['zone_id']
            d = d_dt.setdefault(r['sc_date'], [None,] * len(ZONES))
            if not d[zid]: d[zid] = [0, 0, 0]
            d = d[zid]
            
            if r['sc_flag'] & 0x1:
                d[1] += 1
            else:
                d[0] += 1
            
            if r['sc_flag'] & 0x2:
                d[2] += 1
                
        
        l_dt = d_dt.items()
        l_dt.sort(key=lambda f_x: f_x[0])
        
        dt_1 = datetime.timedelta(1)
        n_dt = []
        sdt = odt
        max_days = MAX_DAYS
        for i in range(len(l_dt)):
            dt,dd = l_dt[i]
            m,d = divmod(dt, 100)
            y,m = divmod(m, 100)
            ndt = datetime.date(y, m, d)
            
            if max_days > 0:
                for j in range((ndt - sdt).days):
                    wd = sdt.weekday()
                    if wd != 6:
                        max_days -= 1
                        n_dt.append( (sdt.strftime("%a (%m/%d)"), None, wd, sdt.year  * 10000 + sdt.month * 100 + sdt.day) )
                        if max_days <= 0: break
                    sdt = sdt + dt_1
            wd = ndt.weekday()
            if wd != 6: max_days -= 1
            n_dt.append( (ndt.strftime("%a (%m/%d)"), dd, wd, ndt.year  * 10000 + ndt.month * 100 + ndt.day) )
            sdt = ndt + dt_1
            
        while max_days > 0:
            wd = sdt.weekday()
            if wd != 6:
                max_days -= 1
                n_dt.append( (sdt.strftime("%a (%m/%d)"), None, wd, sdt.year  * 10000 + sdt.month * 100 + sdt.day) )
            sdt = sdt + dt_1
        
        zones = []
        for j in range(len(ZONES)):
            z,s = ZONES[j]
            f = [0,] * len(n_dt)
            zones.append( (0, f) )
            for i in range(len(n_dt)):
                ss = d_ss.get((n_dt[i][3] << 26) | j)
                if ss != None:
                    f[i] = ss
                elif n_dt[i][2] in s:
                    f[i] = 1
        
        self.req.writejs({'dt': n_dt, 'zones': zones})

    def get_docs(self, date, zone_id, clerk_id, mode=0):
        clerk = None
        if clerk_id:
            clerk = self.finduser(clerk_id)
            if not clerk: return None

        so_sids = set()
        rc_sids = set()
        sc_lst = []
        cur = self.cur()
        if mode:
            where = ' where sc_date>=%s'
        else:
            where = ' where sc_date=%s order by sc_prio desc,sc_id desc'
        cur.execute('select sc_id,sc_date,sc_flag,doc_type,doc_sid from schedule ' + where, (date,))
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            sc_lst.append(r)
            if r['doc_type']:
                rc_sids.add(r['doc_sid'])
            else:
                so_sids.add(r['doc_sid'])
        
        d_so = {}
        if so_sids:
            sql = 'select sid,sonum,clerk,sodate,global_js from sync_salesorders where sid in (%s)' % (','.join(map(str, so_sids)), )
            if clerk:
                cur.execute(sql + ' and clerk=%s', (clerk[1].lower(),))
            else:
                cur.execute(sql)
            for r in cur.fetchall(): d_so[r[0]] = r
            
        d_rc = {}
        if rc_sids:
            sql = 'select sid,num,assoc,order_date,global_js from sync_receipts where sid_type=0 and sid in (%s)' % (','.join(map(str, rc_sids)), )
            if clerk:
                cur.execute(sql + ' and assoc=%s', (clerk[1].lower(),))
            else:
                cur.execute(sql)
            for r in cur.fetchall(): d_rc[r[0]] = r
        
        locs = set()
        for r in sc_lst:
            if r['doc_type']:
                doc_data = d_rc[ r['doc_sid'] ]
            else:
                doc_data = d_so[ r['doc_sid'] ]
            
            r['doc_data'] = doc_data
            doc_js = r['doc_js'] = json.loads(doc_data[4])
            if doc_js['shipping']:
                doc_loc = doc_js['shipping'].get('loc')
            elif doc_js['customer']:
                doc_loc = doc_js['customer'].get('loc')
            
            r['doc_loc'] = doc_loc
            if doc_loc != None:
                doc_loc_dc = r['doc_loc_dc'] = base64.b64decode(doc_loc)
                locs.add(doc_loc_dc)
            
        d_loc = {}
        if locs:
            cur.execute('select loc,zone_id from address where loc in ('+','.join(['%s'] * len(locs))+') and flag!=0', tuple(locs))
            for r in cur.fetchall(): d_loc[ r[0] ] = r[1]
        
        lst = [] 
        for r in sc_lst:
            zid = r['doc_loc'] != None and d_loc.get(r['doc_loc_dc']) or 0
            if zone_id >= 0 and zid != zone_id: continue
            
            doc_js = r['doc_js']
            doc_data = r['doc_data']
            r['zone_id'] = zid
            r['cust_nz'] = (doc_js['customer'] or {}).get('company') or ''
            r['num'] = doc_data[1]
            r['doc_assoc'] = doc_data[2]
            r['doc_date'] = doc_data[3]
            r['doc_amt'] = doc_js['total']
            
            r['doc_js'] = r['doc_data'] = r['doc_loc_dc'] = None
            r['doc_sid'] = str(r['doc_sid'])
            
            lst.append(r)
    
        return lst
        
    def fn_get_docs(self):
        dt = self.qsv_int('dt')
        zone_id = self.qsv_int('zone_id')
        clerk_id = self.qsv_int('clerk_id')
        
        m,d = divmod(dt, 100)
        y,m = divmod(m, 100)
        date = datetime.date(y, m, d)
        if date < datetime.date.today(): self.req.exitjs({'err': -9, 'err_s': "Invalid Date"})
        
        ss = 0
        cur = self.cur()
        cur.execute('select ss_val from schedule_special where ss_date=%s and ss_zidx=%s', (dt, zone_id))
        rows = cur.fetchall()
        if rows:
            ss = rows[0][0]
        elif date.weekday() in ZONES[zone_id][1]:
            ss = 1
        
        self.req.writejs({
            'state': ss,
            'date': dt,
            'zone_nz': ZONES[zone_id][0],
            'zone_id': zone_id,
            'lst': self.get_docs(dt, zone_id, clerk_id, 0)
        })


