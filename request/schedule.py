import json
import time
import config
import datetime

MAX_DAYS = 7
ZONES = (
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
    
    ('*Other*', set([])),
)
WDAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        r = {
            'zones': [ f_x[0] for f_x in ZONES ]
        }
        self.req.writefile('schedule.html', r)
    
    def fn_get_doc(self):
        d_num = self.req.qsv_ustr('num')
        if not d_num.isdigit(): return
        d_type = int(bool(self.req.qsv_int('type')))
        
        cur = self.cur()
        if d_type:
            cur.execute('select sid,assoc,order_date,global_js from sync_receipts where num=%s and sid_type=0 and (type&0xFF)=0 order by sid desc limit 1', (
                int(d_num),
                )
            )
        else:
            cur.execute('select sid,clerk,sodate,global_js from sync_salesorders where sonum=%s and (status>>4)=0 order by sid desc limit 1', (
                d_num,
                )
            )
        
        row = cur.fetchall()
        if not row: self.req.exitjs({'err': -1, 'err_s': 'document #%s not found' % (d_num,)})
        sid,assoc,doc_date,gjs = row[0]
        
        gjs = json.loads(gjs)
        company = (gjs.get('customer') or {}).get('company') or ''
        
        recs = []
        js = {
            'type': d_type,
            'sid':str(sid),
            'assoc': assoc,
            'company': company,
            'total': gjs['total'],
            'recs': recs
        }
        
        cur.execute('select sc_id,sc_date,sc_rev,sc_flag,sc_note from schedule where doc_type=%s and doc_sid=%s order by sc_id asc', (
            d_type, sid
            )
        )
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            r['sc_prio'] = (r['sc_flag'] & 0xF) - 1
            r['sc_flag'] = r['sc_flag'] >> 4
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
        prio = min(max(-1, self.req.psv_int('prio')), 2) + 1
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
            cur.execute('insert into schedule values(null,%s,1,%s,%s,%s,%s)', (
                d_date, prio, d_type, d_sid, note
                )
            )
        else:
            cur.execute("select sc_date,sc_flag from schedule where sc_id=%s and sc_rev=%s", (
                sc_id, rev
                )
            )
            row = cur.fetchall()
            if not row: self.req.exitjs({'err': -3, 'err_s': "document #%s - record #%s - can't find the record" % (d_num, sc_id)})
            old_sc_date,old_sc_flag = row[0]
            if old_sc_date == d_date and (old_sc_flag & 0xF) == prio: self.req.exitjs({'err': -2, 'err_s': "document #%s - record #%s - nothing changed" % (d_num, sc_id)})
            
            cur.execute("update schedule set sc_rev=sc_rev+1,sc_date=%s,sc_flag=%s where sc_id=%s and sc_rev=%s and sc_flag&0x10=0", (
                d_date, (old_sc_flag & ~0xF) | prio, sc_id, rev
                )
            )
            
        rc = cur.rowcount
        if rc <= 0:
            self.req.exitjs({'err': -2, 'err_s': "document #%s - can't make any update" % (d_num, )})
        else:
            pass
            
        self.req.exitjs({'err': 0})
        
    
    def fn_get_overview(self):
        odt = datetime.date.today()
        cdt = odt.year * 10000 + odt.month * 100 + odt.day
        
        d_dt = {}
        cur = self.cur()
        cur.execute('select sc_date,sc_flag,doc_type,doc_sid from schedule where sc_date >= %s', (cdt,))
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            d = d_dt.setdefault(r['sc_date'], [None,] * len(ZONES))
            
            if not d[0]: d[0] = [0, 0, 0]
            d = d[0]
            
            if r['sc_flag'] & 0x10:
                d[1] += 1
            else:
                d[0] += 1
            
            if r['sc_flag'] & 0x20:
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
            
            if max_days:
                for j in range((ndt - sdt).days):
                    wd = sdt.weekday()
                    if wd != 6:
                        max_days -= 1
                        n_dt.append( (sdt.strftime("%a (%m/%d)"), None, wd, sdt.year  * 10000 + sdt.month * 100 + sdt.day) )
                        if max_days <= 0: break
                    sdt = sdt + dt_1
            n_dt.append( (ndt.strftime("%a (%m/%d)"), dd, ndt.weekday(), ndt.year  * 10000 + ndt.month * 100 + ndt.day) )
            sdt = ndt + dt_1
            
        for i in range(max_days):
            wd = sdt.weekday()
            if wd.weekday() != 6:
                max_days -= 1
                n_dt.append( (sdt.strftime("%a (%m/%d)"), None, wd, sdt.year  * 10000 + sdt.month * 100 + sdt.day) )
            sdt = sdt + dt_1
        
        zones = []
        for z,s in ZONES:
            f = [0,] * len(n_dt)
            zones.append( (0, f) )
            for i in range(len(n_dt)):
                if n_dt[i][2] in s:
                    f[i] = 1
        
        self.req.writejs({'dt': n_dt, 'zones': zones})

    def fn_get_docs(self):
        dt = self.qsv_int('dt')
        zidx = self.qsv_int('zidx')
        
        
        
        
