import json
import time
import config
import datetime


STATIONS_MAP = {
    13: 1,
    8: 2,
    12: 3,
    6: 3,
    3: 3
}


DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('cash_drawer.html')
        
    def get_total_by_station(self, station, cur_ts=None):
        tp = time.localtime(cur_ts)
        frm_dt = datetime.date(tp.tm_year, tp.tm_mon, tp.tm_mday)
        frm_ts = int(time.mktime(frm_dt.timetuple()))
        to_dt = frm_dt + datetime.timedelta(1)
        to_ts = int(time.mktime(to_dt.timetuple()))
        
        total = ([0, 0], [0, 0])
        
        cur = self.cur()
        cur.execute('select global_js from sync_receipts where sid_type=0 and (type&0xFF)=0 and order_date>=%s and order_date<%s', (
            frm_ts, to_ts
            )
        )
        nzs = cur.column_names
        for r in cur:
            r = dict(zip(nzs, r))
            
            glbs = json.loads(r['global_js'])
            sidx = STATIONS_MAP.get(int(glbs.get('station') or 0), 4)
            if sidx != station: continue
            
            for v in glbs['tender']:
                if v['type'] == 1:
                    total[0][0] += v['amount']
                    total[0][1] += 1
                elif v['type'] == 2:
                    total[1][0] += v['amount']
                    total[1][1] += 1
                    
        return total

    def fn_get_total_by_station(self):
        station = self.req.qsv_int('station')
        self.req.writejs( self.get_total_by_station(station) )

    def fn_save(self):
        station = self.req.psv_int('station')
        if station < 1 or station > len(STATIONS): return
        
        cur_ts = int(time.time())
        
        reason = self.req.psv_ustr('reason')
        begin_amt = float(self.req.psv_str('begin_amt') or 0.0)
        count_amt = float(self.req.psv_str('count_amt') or 0.0)
        check_amt = float(self.req.psv_str('check_amt') or 0.0)
        total = self.get_total_by_station(station, cur_ts)
        
        err_amt = round(begin_amt + total[0][0] + total[1][0] - count_amt - check_amt, 2)
        if err_amt and not reason: self.req.exitjs({'ret': 1, 'err_amt': err_amt})

        js = {'cash': count_amt, 'check': check_amt, 'begin': begin_amt, 'reason': reason, 'total': total}
        cur = self.cur()
        cur.execute('insert into cashdrawer values(null,%s,%s,%s,%s)', (
            station,
            int(err_amt * 100),
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
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select SQL_CALC_FOUND_ROWS rid,sid,err,ts,js from cashdrawer order by rid desc limit %d,%d' % (
                sidx * pgsz, (eidx - sidx) * pgsz
                )
            )
            for r in cur.fetchall():
                rid,sid,err,ts,js = r
                js = json.loads(js)
                if err:
                    err_s = '$%0.2f, %s' % (err / 100.0, js.get('reason', ''))
                else:
                    err_s = ''
                r = (
                    rid,
                    sid,
                    err_s,
                    time.strftime("%m/%d/%y %I:%M:%S %p", time.localtime(ts)),
                    js,
                )
                apg.append(r)
        
            cur.execute('select FOUND_ROWS()')
            
        else:
            cur.execute('select count(*) from cashdrawer')
            
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)

    def fn_report(self):
        self.req.writefile('cash_drawer_report.html')

    def fn_get_report(self):
        cur_ts = self.req.qsv_int('frm_date') or int(time.time())
        tp = time.localtime(cur_ts)
        frm_dt = datetime.date(tp.tm_year, tp.tm_mon, tp.tm_mday)
        frm_ts = int(time.mktime(frm_dt.timetuple()))
        to_dt = frm_dt + datetime.timedelta(1)
        to_ts = int(time.mktime(to_dt.timetuple()))
        
        ret = []
        cur = self.cur()
        cur.execute('select rid,sid,err,ts,js from cashdrawer where ts>=%s and ts<%s order by rid asc' % (
            frm_ts, to_ts
            )
        )
        for r in cur.fetchall():
            rid,sid,err,ts,js = r
            js = json.loads(js)
            if err:
                err_s = '$%0.2f, %s' % (err / 100.0, js.get('reason', ''))
            else:
                err_s = ''
            ret.append((
                rid,
                sid,
                err_s,
                time.strftime("%m/%d/%y %I:%M:%S %p", time.localtime(ts)),
                js,
            ))
        
        self.req.writejs(ret)

