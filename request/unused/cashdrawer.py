import json
import time
import config
import datetime


STATIONS_MAP = {
    13: 1,
    8: 2,
    
    12: 3,
    6: 3,
    3: 3,
    24: 3,
    23: 3,
    25: 3,
    
}
DEFAULT_STATION_ID = 9

DEFAULT_BEGIN_CASH_AMOUNT = 198.25



DEFAULT_PERM = 1 << config.USER_PERM_BIT['cashier']
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        r = {
            'is_sale_mgr': (1 << config.USER_PERM_BIT['sales_mgr']) & self.user_lvl
        }
        self.req.writefile('cash_drawer.html', r)
        
    def get_total(self, cur_ts=None):
        tp = time.localtime(cur_ts)
        frm_dt = datetime.date(tp.tm_year, tp.tm_mon, tp.tm_mday)
        frm_ts = int(time.mktime(frm_dt.timetuple()))
        to_dt = frm_dt + datetime.timedelta(1)
        to_ts = int(time.mktime(to_dt.timetuple()))
        
        total = {}
        
        cur = self.cur()
        cur.execute('select cashier,global_js from sync_receipts where sid_type=0 and (type&0xFF)=0 and order_date>=%s and order_date<%s', (
            frm_ts, to_ts
            )
        )
        nzs = cur.column_names
        for r in cur:
            r = dict(zip(nzs, r))
            
            glbs = json.loads(r['global_js'])
            sid = STATIONS_MAP.get(int(glbs.get('station') or 0), DEFAULT_STATION_ID)
            s = total.setdefault(sid, [[DEFAULT_BEGIN_CASH_AMOUNT, 0], [0, 0, []], set(), DEFAULT_BEGIN_CASH_AMOUNT])
            
            for v in glbs['tender']:
                if v['type'] == 1:
                    s[0][0] += v['amount']
                    s[0][1] += 1
                    s[2].add((r['cashier'] or '').lower())
                elif v['type'] == 2:
                    s[1][0] += v['amount']
                    s[1][1] += 1
                    s[1][2].append(v['numlst'])
                    s[2].add((r['cashier'] or '').lower())
        
        for k,v in total.items():
            if not v[0][1] and not v[1][1]:
                del total[k]
            else:
                v[2] = list(v[2])
        return total

    def get_total_by_station(self, station, cur_ts=None):
        total = self.get_total(cur_ts)
        return total.get(station)

    def fn_get_total(self):
        total = self.get_total()
        
        perm = 1 << config.USER_PERM_BIT['sales_mgr']
        if not (perm & self.user_lvl):
            _total = {}
            cur_user_name = self.user_name.lower()
            for k,v in total.items():
                if cur_user_name not in v[2]: continue
                _total[ str(k) ] = v
            total = _total
        else:
            total = dict([(str(f_x), f_v) for f_x,f_v in total.items()])
            
        self.req.writejs({'total': total, 'stations': sorted(total.keys())})

    def fn_view_record(self):
        rid = self.qsv_int('rid')
        
        where_s = ''
        if not((1 << config.USER_PERM_BIT['sales_mgr']) & self.user_lvl): where_s = ' and uid=%d' % (self.user_id,)
        
        cur = self.cur()
        cur.execute('select * from cashdrawer where rid=%s' + where_s, (rid,))
        rows = cur.fetchall()
        if not rows: return
        nzs = cur.column_names
        rec = dict(zip(nzs, rows[0]))
        js = rec['js'] = json.loads(rec['js'])
        
        rec['ds'] = time.strftime("%m/%d/%y %I:%M:%S %p", time.localtime(rec['ts']))

        rec['cash_status'] = ''
        rec['check_status'] = ''
        
        status = 'OK'
        if rec['diff']:
            if rec['diff'] > 0:
                status = 'overage $%0.2f' % (rec['diff'] / 100.0, )
            else:
                status = 'shortage $%0.2f' % (-rec['diff'] / 100.0, )
                
            status += ', ' + js['reason']
                
            cash_diff = js['cash'] - js['total'][0][0]
            if cash_diff:
                if cash_diff > 0:
                    rec['cash_status'] = 'overage $%0.2f' % (cash_diff, )
                else:
                    rec['cash_status'] = 'shortage $%0.2f' % (cash_diff, )
            
            check_diff = js['check'] - js['total'][1][0]
            if check_diff:
                if check_diff > 0:
                    rec['check_status'] = 'overage $%0.2f' % (check_diff, )
                else:
                    rec['check_status'] = 'shortage $%0.2f' % (check_diff, )
                
        rec['status'] = status
        
        rec['user'] = self.finduser(rec['uid'])
        if (rec['flag'] & 1): rec['s_user'] = self.finduser(js['s_uid'])
         
        self.req.writefile('cash_drawer_record.html', {'rec': rec})

    def fn_approve(self):
        rid = self.req.psv_int('rid')
        cur = self.cur()
        cur.execute('select * from cashdrawer where rid=%s and flag&1=0', (rid,))
        rows = cur.fetchall()
        if not rows: return
        nzs = cur.column_names
        rec = dict(zip(nzs, rows[0]))
        js = rec['js'] = json.loads(rec['js'])
        js['s_uid'] = self.user_id
        
        cur.execute('update cashdrawer set flag=flag|1,js=%s where rid=%s and flag&1=0', (
            json.dumps(js, separators=(',',':')), rid,
            )
        )
        ret = cur.rowcount
        self.req.writejs({'ret': ret})
    
    fn_approve.PERM = 1 << config.USER_PERM_BIT['sales_mgr']
    
    def fn_delete(self):
        where_s = ''
        if not((1 << config.USER_PERM_BIT['sales_mgr']) & self.user_lvl): where_s = ' and uid=%d' % (self.user_id,)
        
        rid = self.req.psv_int('rid')
        cur = self.cur()
        cur.execute('delete from cashdrawer where rid=%s and flag&1=0' + where_s, (rid,))
        ret = cur.rowcount
        
        self.req.writejs({'ret': ret})

    def fn_save(self):
        js = self.req.psv_js('js')
        
        station = int(js['station'])
        cur_ts = int(time.time())
        
        reason = js['reason'].strip()
        cash = float(js['cash'])
        check = float(js['check'])
        
        cash_lst = dict([ ('%0.2f' % (float(f_k), ), int(f_x)) for f_k,f_x in js['cash_lst'].items() if f_k != 'sum'])
        check_lst = [ (float(f_k), f_x.strip()) for f_k,f_x in js['check_lst'] ]
        
        total = self.get_total_by_station(station, cur_ts)
        if not total: return
        perm = 1 << config.USER_PERM_BIT['sales_mgr']
        if not(perm & self.user_lvl) and self.user_name.lower() not in total[2]: return
        
        diff = round(cash - total[0][0] + check - total[1][0], 2)
        if diff and not reason: self.req.exitjs({'ret': -1, 'err': 'Require A Reason'})

        js = {'cash': cash,
              'check': check,
              'reason': diff and reason or '',
              'total': total,
              'cash_lst': cash_lst,
              'check_lst': check_lst,
        }
        cur = self.cur()
        
        tp = time.localtime(cur_ts)
        frm_dt = datetime.date(tp.tm_year, tp.tm_mon, tp.tm_mday)
        frm_ts = int(time.mktime(frm_dt.timetuple()))
        to_dt = frm_dt + datetime.timedelta(1)
        to_ts = int(time.mktime(to_dt.timetuple()))
        
        cur.execute('select count(*) from cashdrawer where sid=%s and ts>=%s and ts<%s', (
            station, frm_ts, to_ts
            )
        )
        if cur.fetchall()[0][0]: self.req.exitjs({'ret': -1, 'err': 'Duplicated'})
        
        cur.execute('insert into cashdrawer values(null,0,%s,%s,%s,%s,%s)', (
            station,
            self.user_id,
            int(diff * 100),
            cur_ts,
            json.dumps(js, separators=(',',':'))
            )
        )
        rid = cur.lastrowid

        self.req.exitjs({'ret': 0, 'rid': rid})


    def fn_get_lst(self):
        ret = {'res':{'len':0, 'apg':[]}}

        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        where_s = ''
        if not((1 << config.USER_PERM_BIT['sales_mgr']) & self.user_lvl): where_s = ' where uid=%d' % (self.user_id,)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select SQL_CALC_FOUND_ROWS rid,sid,uid,flag,diff,ts,js from cashdrawer'+where_s+' order by rid desc limit %d,%d' % (
                sidx * pgsz, (eidx - sidx) * pgsz
                )
            )
            nzs = cur.column_names
            for r in cur:
                r = dict(zip(nzs, r))
                js = r['js'] = json.loads(r['js'])
                if r['diff']:
                    err_s = '$%0.2f, %s' % (r['diff'] / 100.0, js.get('reason', ''))
                else:
                    err_s = ''
                r = (
                    time.strftime("%m/%d/%y %I:%M:%S %p", time.localtime(r['ts'])),
                    r['sid'],
                    (r['flag'] & 1) and 'Y' or '',
                    err_s,
                    r['rid'],
                    r
                )
                apg.append(r)
        
            cur.execute('select FOUND_ROWS()')
            
        else:
            cur.execute('select count(*) from cashdrawer'+where_s)
            
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)


