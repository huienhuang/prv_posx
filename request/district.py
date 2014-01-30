import json
import time
import config
import datetime



DAY_SECS = 3600 * 24
WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('district.html')
    
    def fn_load_dists(self):
        dt = self.req.qsv_ustr('dt')
        dt = self.parse_date_century(dt) or 0
        if dt: dt = dt[0] * 10000 + dt[1] * 100 + dt[2]
        
        lst = self.getconfigv2('district_mapping')
        dists = lst and json.loads(lst) or []
        
        cur = self.cur()
        cur.execute('select zip from sync_customers where zip != 0 group by zip order by zip asc')
        zips = [ '%05d' % f_x[0] for f_x in cur.fetchall() ]
    
        cur.execute('select delivery_zip,count(*) from salesorder where delivery_date=%s and delivery_zip!=0 group by delivery_zip', (dt, ))
        stats = {}
        for r in cur.fetchall(): stats['%05d' % r[0]] = r[1]
        
        self.req.writejs({'zips': zips, 'dists': dists, 'stats': stats})
    
    def fn_save_zip_mapping(self):
        js = self.req.psv_js('js')
        
        lst = []
        for x in js:
            if x.get('deleted'): continue
            zips = set([ int(f_x.strip()) for f_x in x['zips'].strip().split(',') if f_x.strip().isdigit() ])
            if not zips: continue
            zips = [ '%05d' % f_x for f_x in sorted(list(zips)) ]
            lst.append([x['name'].strip(), zips])
        
        lst.sort(key=lambda f_x: f_x[0].lower())
        self.setconfigv2('district_mapping', json.dumps(lst, separators=(',',':')))
        
        self.req.writejs({'ret': 1})
    
    
    def fn_get_periods(self):
        date = self.req.qsv_ustr('date')
        rule = self.req.qsv_ustr('rule')
        next_date = self.req.qsv_ustr('next')
        
        date = self.parse_date_century(date)
        if not date: return
        
        rule = self.parse_rule_no_check(rule)
        if not rule: return
        
        next_date = self.parse_date_century(next_date)
        
        t_dt = datetime.date.today()
        t_dt = (t_dt.year, t_dt.month, t_dt.day)
        if next_date and next_date > t_dt: t_dt = next_date
        
        periods = self.get_periods(date, rule, t_dt, 5)
        if not periods: return
        res = []
        for p in periods:
            s = time.localtime(p[0])
            e = time.localtime(p[1] - 11 * 3600)
            res.append((
                time.strftime("%m/%d/%Y", s) + ' ' + WEEKDAYS[ s.tm_wday ],
                time.strftime("%m/%d/%Y", e) + ' ' + WEEKDAYS[ e.tm_wday ]
            ))
        
        self.req.writejs(res)
        
    
    def get_periods(self, schedule_date, a_rule, target_date, period_len):
        res = self.get_period(schedule_date, a_rule, target_date)
        if not res: return
        frm_ts, to_ts, s_ts, t_ts, k = res
        
        periods = [ (frm_ts, to_ts) ]
        start_ts = to_ts
        i = 0
        while i < period_len:
            k = (k + 1) % len(a_rule)
            d = a_rule[k]
            end_ts = start_ts + d[1] * DAY_SECS
            if not d[0]:
                i += 1
                periods.append( (start_ts, end_ts) )
            start_ts = end_ts
            
        return periods
    
    def get_period(self, schedule_date, a_rule, target_date):
        if not a_rule: return
        target_date = max(schedule_date, target_date)
        
        s_dt = datetime.date(*schedule_date)
        t_dt = datetime.date(*target_date)
        
        s_ts = time.mktime(s_dt.timetuple())
        t_ts = time.mktime(t_dt.timetuple())
        
        frm_ts = s_ts
        k = 0
        while True:
            d = a_rule[k]
            to_ts = frm_ts + d[1] * DAY_SECS
            if not d[0] and t_ts < to_ts: return (frm_ts, to_ts, s_ts, t_ts, k)
            frm_ts = to_ts
            k = (k + 1) % len(a_rule)
    
    def parse_rule(self, s):
        a = []
        k = 0
        for x in s.split(','):
            x = x.strip()
            if not x: continue
            c = ''
            if x[-1:] == 'p':
                c = x[-1:]
                x = x[:-1]
            if not x.isdigit() or not int(x): continue
            a.append((x, c))
            if not c: k += 1
        
        return k and a or []
    
    def parse_rule_no_check(self, s):
        a = []
        k = 0
        for x in s.split(','):
            if not x[-1:].isdigit():
                a.append( (ord(x[-1:]), int(x[:-1])) )
            else:
                a.append( (0, int(x)) )
                k += 1
    
        return k and a or []
    
    def parse_date_century(self, s):
        if not s: return
        t_mon,t_day,t_year = map(int, s.split('/'))
        if t_mon < 1 or t_mon > 12: return
        if t_day < 1 or t_day > 31: return
        if t_year < 2000 or t_year > 2099: return
    
        return (t_year, t_mon, t_day)
    
    def fn_get_dist_customers(self):
        zips = self.req.qsv_ustr('zips')
        if not zips: return
        zips = set(map(int, zips.split(',')))
        if not zips: return
        
        t_dt = self.parse_date_century(self.req.qsv_ustr('delivery_date'))
        if not t_dt: return
        t_year,t_mon,t_day = t_dt
        t_ts = time.mktime(datetime.date(*t_dt).timetuple())
        
        cur = self.cur()
        
        custs_marked_count = {}
        dt = t_year * 10000 + t_mon * 100 + t_day
        cur.execute('select sso.cust_sid,count(*) from salesorder so left join sync_salesorders sso on (so.sid=sso.sid) where sso.sid is not null and sso.status<=1 and so.delivery_date=%s group by sso.cust_sid', (
            dt,
            )
        )
        for r in cur.fetchall(): custs_marked_count.setdefault(r[0], [0])[0] += r[1]
        
        cur.execute(('select sc.sid,sc.name,sc.zip,c.schedule_date,c.schedule_rule,c.schedule_next,(select max(sodate) from sync_salesorders where cust_sid=sc.sid and status<=1) as so_maxdate from sync_customers sc left join customer c on (c.cid=sc.sid) where c.cid is not null and c.schedule_date!=0 and sc.zip in (%s)') % (','.join(map(str, zips)),))
        cnz = cur.column_names
        rows = []
        for r in cur.fetchall():
            r = dict(zip(cnz, r))
            m_r,m_day = divmod(r['schedule_date'], 100)
            m_year,m_mon = divmod(m_r, 100)
            s_dt = (m_year, m_mon, m_day)
            
            a_dt = t_dt
            if r['schedule_next']:
                m_r,m_day = divmod(r['schedule_next'], 100)
                m_year,m_mon = divmod(m_r, 100)
                n_dt = (m_year, m_mon, m_day)
                if n_dt > a_dt: a_dt = n_dt
                
            period = self.get_period(s_dt, self.parse_rule_no_check(r['schedule_rule']), a_dt)

            cur.execute('select ss.sid,(select sid from sync_receipts where so_sid=ss.sid limit 1) from sync_salesorders ss where ss.cust_sid=%s and ss.sodate>=%s and ss.sodate<%s and ss.status<=1', (
                r['sid'], period[0], period[1]
                )
            )
            so_count = rc_count = 0
            for row in cur.fetchall():
                so_count += 1
                if row[1] != None: rc_count += 1
            
            r['rc_count'] = rc_count
            r['so_count'] = so_count
            so_maxdate = r['so_maxdate']
            r['so_maxdate'] = so_maxdate and time.strftime("%m/%d/%Y", time.localtime(so_maxdate)) or ''
            ps_dt = time.localtime(period[0])
            r['period_start'] = time.strftime("%m/%d/%Y", ps_dt)
            pe_dt = time.localtime(period[1] - 11 * 3600)
            r['period_end'] = time.strftime("%m/%d/%Y", pe_dt)
            not_in_range = r['not_in_range'] = int(t_ts < period[0] or t_ts >= period[1])
            
            ps_dt = ps_dt.tm_year * 10000 + ps_dt.tm_mon * 100 + ps_dt.tm_mday
            pe_dt = pe_dt.tm_year * 10000 + pe_dt.tm_mon * 100 + pe_dt.tm_mday
            cur.execute('select count(*) from salesorder s left join sync_salesorders ss on (s.sid=ss.sid) where s.delivery_date>=%s and s.delivery_date<=%s and ss.cust_sid=%s and ss.status<=1', (
                ps_dt, pe_dt, r['sid']
                )
            )
            r['period_marked_count'] = cur.fetchall()[0][0]
            
            r['marked_count'] = custs_marked_count.get(r['sid'], [0])[0]
            r['sid'] = str(r['sid'])
            
            rows.append( ((not_in_range, int(bool(so_count)), abs(period[1] - t_ts)), r) )
            
        rows.sort(key=lambda x:x[0])
        rows = [ x[1] for x in rows ]
        
        self.req.writejs(rows)
    
    def fn_set_schedule(self):
        cid = self.req.psv_int('cid')
        note = self.req.psv_ustr('note')[:512]
        date = self.req.psv_ustr('date')
        rule = self.req.psv_ustr('rule')
        next_date = self.req.psv_ustr('next')
        
        date = self.parse_date_century(date) or 0
        if date: date = date[0] * 10000 + date[1] * 100 + date[2]
        
        next_date = self.parse_date_century(next_date) or 0
        if next_date: next_date = next_date[0] * 10000 + next_date[1] * 100 + next_date[2]
        
        rule = self.parse_rule(rule)
        if not rule: date = 0
        rule = ','.join([f_x[0] + f_x[1] for f_x in rule])
        
        cur = self.cur()
        cur.execute('insert into customer values (%s,%s,%s,%s,%s) on duplicate key update schedule_date=%s,schedule_rule=%s,schedule_next=%s,note=%s', (
            cid, date, rule, next_date, note, date, rule, next_date, note
            )
        )
        
        self.req.writejs({'ret': 1})
        
    def fn_get_schedule(self):
        cid = self.req.psv_int('cid')
        
        cur = self.cur()
        cur.execute('select cid,schedule_date,schedule_rule,schedule_next,note from customer where cid=%s', (cid,))
        rows = cur.fetchall()
        if not rows: return
        row = dict(zip(cur.column_names, rows[0]))
        
        if row['schedule_date']:
            m_r,m_day = divmod(row['schedule_date'], 100)
            m_year,m_month = divmod(m_r, 100)
            row['schedule_date'] = '%02d/%02d/%04d' % (m_month, m_day, m_year)
        else:
            row['schedule_date'] = ''
            
        if row['schedule_next']:
            m_r,m_day = divmod(row['schedule_next'], 100)
            m_year,m_month = divmod(m_r, 100)
            row['schedule_next'] = '%02d/%02d/%04d' % (m_month, m_day, m_year)
        else:
            row['schedule_next'] = ''
            
        self.req.writejs(row)
    
    
    def fn_get_marked_salesorders(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        sid = self.req.qsv_int('sid')
        frm_date = self.req.qsv_ustr('frm')
        to_date = self.req.qsv_ustr('to')
        
        frm_date = self.parse_date_century(frm_date) or 0
        if frm_date: frm_date = frm_date[0] * 10000 + frm_date[1] * 100 + frm_date[2]
        
        to_date = self.parse_date_century(to_date) or 0
        if to_date: to_date = to_date[0] * 10000 + to_date[1] * 100 + to_date[2]
        
        if not frm_date or not to_date or frm_date > to_date: self.req.exitjs(ret)
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select SQL_CALC_FOUND_ROWS ss.sonum,s.delivery_zip,s.sid,ss.cust_sid,ss.global_js,s.delivery_date from salesorder s left join sync_salesorders ss on (s.sid=ss.sid) where s.delivery_date>=%d and s.delivery_date<=%d and ss.cust_sid=%d and ss.status<=1 order by s.delivery_date desc,s.sid desc limit %d,%d' % (
                        frm_date, to_date, sid, sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                r = list(r)
                global_js = json.loads(r[4])
                company = (global_js.get('customer') or {}).get('company') or ''
                
                m_r,m_day = divmod(r[5], 100)
                m_year,m_month = divmod(m_r, 100)
                schedule_date = '%02d/%02d/%04d' % (m_month, m_day, m_year)
            
                apg.append((r[0], company, r[1], schedule_date, str(r[2]), str(r[3])))
                
            cur.execute('select FOUND_ROWS()')
        else:
            cur.execute('select count(*) from salesorder s left join sync_salesorders ss on (s.sid=ss.sid) where s.delivery_date>=%d and s.delivery_date<=%d and ss.cust_sid=%d and ss.status<=1' % (
                frm_date, to_date, sid
                )
            )
        
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
    
    def fn_get_salesorders(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        zips = self.req.qsv_ustr('zips')
        if not zips: return
        zips = set(map(int, zips.split(',')))
        if not zips: return
        
        date = self.req.qsv_ustr('date')
        date = self.parse_date_century(date) or 0
        if date: date = date[0] * 10000 + date[1] * 100 + date[2]
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select SQL_CALC_FOUND_ROWS sso.sonum,so.delivery_zip,so.sid,sso.cust_sid,sso.global_js from salesorder so left join sync_salesorders sso on(so.sid=sso.sid) where sso.sid is not null and so.delivery_date=%d and so.delivery_zip in (%s) limit %d,%d' % (
                        date, ','.join(map(str, zips)), sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                r = list(r)
                global_js = json.loads(r[4])
                company = (global_js.get('customer') or {}).get('company') or ''
                apg.append((r[0], company, r[1], str(r[2]), str(r[3])))
                
            cur.execute('select FOUND_ROWS()')
        else:
            cur.execute('select count(*) from salesorder so left join sync_salesorders sso on(so.sid=sso.sid) where sso.sid is not null and so.delivery_date=%s and so.delivery_zip in (%s)' % (
                date, ','.join(map(str, zips))
                )
            )
        
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
    
    def salesorder_setup(self, row):
        cur = self.cur()
        cur.execute('select sid,sid_type,num from sync_receipts where so_sid=%s order by sid asc limit 1', (row['sid'],))
        rows = cur.fetchall()
        if rows:
            row['ref_receipt'] = map(str, rows[0])
        else:
            row['ref_receipt'] = None
            
        row['sid'] = str(row['sid'])
        row['cust_sid'] = str(row['cust_sid'])
        
        global_js = json.loads(row['global_js'])
        customer = global_js.get('customer') or {}
        row['name'] = customer.get('company') or ''
        row['marked'] = int(bool(row['delivery_zip'] or row['delivery_date']))
        
        zipcode = row['delivery_zip']
        if not zipcode:
            zipcode = (global_js.get('shipping') or {}).get('zip')
            if not zipcode: zipcode = customer.get('zip')
        
        zipcode = str(zipcode or '').split('-')[0].strip()[:5]
        if zipcode and zipcode.isdigit() and len(zipcode) <= 5:
            zipcode = int(zipcode)
        else:
            zipcode = 0
        row['delivery_zip'] = '%05d' % zipcode
        
        if row['delivery_date']:
            m_r,m_day = divmod(row['delivery_date'], 100)
            m_year,m_month = divmod(m_r, 100)
            row['delivery_date'] = '%02d/%02d/%04d' % (m_month, m_day, m_year)
        else:
            row['delivery_date'] = ''
        
        row['global_js'] = None
    
    def fn_get_salesorder(self):
        sonum = self.req.qsv_str('sonum')
        if not sonum: return
        
        cur = self.cur()
        cur.execute('select sso.sid,sso.sonum,sso.cust_sid,so.delivery_date,so.delivery_zip,sso.global_js,c.schedule_date from sync_salesorders sso left join salesorder so on (sso.sid=so.sid) left join customer c on(sso.cust_sid=c.cid) where sso.sonum=%s and sso.status<=1', (sonum,))
        rows = cur.fetchall()
        if not rows: return
        row = dict(zip(cur.column_names, rows[0]))
        self.salesorder_setup(row)
        self.req.writejs(row)
    
    def fn_set_salesorders_delivery(self):
        js = self.req.psv_js('js')
        if not js: return
        
        rs = {}
        for r in js:
            sid = int(r[0])
            i_date = self.parse_date_century(r[1]) or 0
            if i_date: i_date = i_date[0] * 10000 + i_date[1] * 100 + i_date[2]
            i_zip = int(r[2])
            rs[sid] = (i_date, i_zip)
        if not rs: return
        
        s_rs = []
        cur = self.cur()
        cur.execute('select sid from sync_salesorders where sid in (%s) and status<=1' % (','.join(map(str, rs.keys())),) )
        for r in cur.fetchall():
            i_date,i_zip = rs.get(r[0])
            cur.execute('insert into salesorder values (%s,%s,%s) on duplicate key update delivery_date=%s,delivery_zip=%s', (
                r[0], i_date, i_zip, i_date, i_zip
                )
            )
        
        self.req.writejs({'ret':1})

    def fn_get_cust_salesorders(self):
        sid = self.req.qsv_int('sid')
        frm = self.req.qsv_ustr('frm')
        frm = self.parse_date_century(frm) or 0
        to = self.req.qsv_ustr('to')
        to = self.parse_date_century(to) or 0
        if not frm or not to: return
        
        frm_ts = time.mktime(datetime.date(*frm).timetuple())
        to_ts = time.mktime(datetime.date(*to).timetuple()) + DAY_SECS
        
        cur = self.cur()
        cur.execute('select sso.sid,sso.sonum,sso.cust_sid,so.delivery_date,so.delivery_zip,sso.global_js,c.schedule_date from sync_salesorders sso left join salesorder so on (sso.sid=so.sid) left join customer c on(sso.cust_sid=c.cid) where sso.cust_sid=%s and sso.sodate>=%s and sso.sodate<%s and sso.status<=1 order by sso.sid desc', (
                sid, frm_ts, to_ts
            )
        )
        rows = []
        col_nzs = cur.column_names
        for row in cur.fetchall():
            row = dict(zip(col_nzs, row))
            self.salesorder_setup(row)
            rows.append(row)
            
        self.req.writejs(rows)
        
        