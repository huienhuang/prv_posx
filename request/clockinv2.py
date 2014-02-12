import config
import hashlib
import json
import time
import datetime
import random
import cStringIO
import csv

HIST_FLAG_TYPE = 1 << 0
HIST_FLAG_STATUS = 1 << 1

DAY_SECS = 3600 * 24
DAY_OVERTIME_SECS = 8 * 3600

WEEK_OVERTIME_SECS = 40 * 3600

WEEK_START_DAY = (2014, 1, 1)
WEEK_SECS = DAY_SECS * 7


DEFAULT_PERM = 1 << config.USER_PERM_BIT['time']
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('clockin_v2.html')
        
    fn_default.PERM = 0

    def fn_get_user_info(self):
        ret = {}
        code = self.req.psv_int('code')
        if not code: self.req.exitjs(ret)
        
        cur = self.cur()
        cur.execute('select c.user_id,c.user_code,c.in_ts,c.rev,u.user_name,c.flag from clockin_user c left join user u on (c.user_id=u.user_id) where c.user_code=%s', (code,))
        rows = cur.fetchall()
        if not rows: self.req.exitjs(ret)
        nzs = cur.column_names
        user = dict(zip(nzs, rows[0]))
        
        frm_ts = self.get_day_ts(user['in_ts'] or None)
        to_ts = frm_ts + DAY_SECS
        
        secs = 0
        stat = self.get_user_hist_stat(frm_ts, to_ts, user['user_id']).get(user['user_id'], {}).get(frm_ts)
        if stat: secs += stat[2]
        ts = int(time.time())
        if user['in_ts'] and ts > user['in_ts']: secs += ts - user['in_ts']
        if secs: user['today_hrs'] = self.get_str_time(secs)
        
        ret['user'] = user
        self.req.writejs(ret)
        
    fn_get_user_info.PERM = 0
    
    def fn_clockin(self):
        ret = {}
        code = self.req.psv_int('code')
        if not code: self.req.exitjs(ret)
        rev = self.req.psv_int('rev')
        u_in = self.req.psv_int('in')
        
        cur = self.cur()
        cur.execute('select * from clockin_user where user_code=%s and rev=%s', (code, rev))
        rows = cur.fetchall()
        if not rows: self.req.exitjs(ret)
        nzs = cur.column_names
        user = dict(zip(nzs, rows[0]))
        if not(bool(u_in) ^ bool(user['in_ts'])): self.req.exitjs(ret)
        
        ts = int(time.time())
        cur.execute('update clockin_user set in_ts=%s,rev=rev+1 where user_id=%s and rev=%s', (
            u_in and ts or 0, user['user_id'], rev
            )
        )
        if cur.rowcount:
            if not u_in:
                cur.execute("insert into clockin_hist values (null,%s,%s,%s,'',0)", (
                    user['user_id'], user['in_ts'], ts
                    )
                )
            ret['ret'] = 1
            
        self.req.writejs(ret)

    fn_clockin.PERM = 0

    def fn_mgr(self):
        self.req.writefile('clockin_v2_mgr.html')
    
    def fn_loads_users(self):
        cur = self.cur()
        cur.execute('select u.user_id,u.user_name,c.user_id as c_user_id,c.user_code,c.in_ts,c.flag,c.rev from user u left join clockin_user c on (c.user_id=u.user_id) order by u.user_name asc')
        nzs = cur.column_names
        normal_users = []
        clockin_users = []
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            r['in_time'] = r['in_ts'] and time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(r['in_ts'])) or ''
            if r['c_user_id']:
                clockin_users.append(r)
            else:
                normal_users.append(r)
                
        self.req.writejs( {'normal_users': normal_users, 'clockin_users': clockin_users} )
    
    def fn_add_clockin_user(self):
        user_id = self.req.psv_int('user_id')
        user_code = self.req.psv_int('user_code')
        cur = self.cur()
        cur.execute('select count(*) from user where user_id=%s', (user_id,))
        if not cur.fetchall()[0][0]: return
        cur.execute('insert ignore into clockin_user values (%s,%s,0,0,0)', (user_id, user_code))
        
        self.req.writejs({'ret':1})
        
    def fn_del_clockin_user(self):
        user_id = self.req.psv_int('user_id')
        cur = self.cur()
        cur.execute('delete from clockin_user where user_id=%s', (user_id,))
        
        self.req.writejs({'ret':1})
    
    def fn_update_code_clocking_user(self):
        user_id = self.req.psv_int('user_id')
        user_rev = self.req.psv_int('user_rev')
        user_code = self.req.psv_int('user_code')
        user_lang = self.req.psv_int('user_lang')
        cur = self.cur()
        flag_s = user_lang and '|1' or '&~1'
        cur.execute('update clockin_user set user_code=%s,flag=flag'+flag_s+',rev=rev+1 where user_id=%s and rev=%s', (
            user_code, user_id, user_rev
            )
        )
        ret = cur.rowcount
        
        self.req.writejs({'ret':ret})
        
    def fn_update_status_clocking_user(self):
        user_id = self.req.psv_int('user_id')
        user_rev = self.req.psv_int('user_rev')
        user_in = self.req.psv_int('user_in')
        user_in_time = self.req.psv_ustr('user_in_time')
        cur = self.cur()
        
        in_ts = user_in and int(time.mktime(time.strptime(user_in_time, '%m/%d/%Y %I:%M:%S %p'))) or 0
        cur.execute('update clockin_user set in_ts=%s,rev=rev+1 where user_id=%s and rev=%s', (
            in_ts, user_id, user_rev
            )
        )
        ret = cur.rowcount
        
        self.req.writejs({'ret':ret})
    
    def get_day_ts(self, ts=None):
        tp = time.localtime(ts)
        ts = int(time.mktime(datetime.date(tp.tm_year, tp.tm_mon, tp.tm_mday).timetuple()))
        return ts
    
    def get_users_stat(self, frm_ts, to_ts):
        fw_ts = int(time.mktime(datetime.date(*WEEK_START_DAY).timetuple()))
        users_lku = dict([(u[0], u[1]) for u in self.getuserlist()])
        users = self.get_user_hist_stat(frm_ts, to_ts)

        data = []
        for user_id,days in users.items():
            total = [0, 0, 0, 0, 0]
            week_overtime = {}
            for day,stat in days.items():
                first_in_ts,last_out_ts,total_secs,count = stat[:4]
                normal_secs = min(total_secs, DAY_OVERTIME_SECS)
                overtime_secs = max(total_secs - DAY_OVERTIME_SECS, 0)
                total[0] += total_secs
                total[1] += normal_secs
                total[3] += overtime_secs
                if day >= fw_ts: week_overtime.setdefault(int((day - fw_ts)/WEEK_SECS), [0])[0] += normal_secs
            
            wot_lst = []
            for widx,secs in sorted(week_overtime.items(), key=lambda f_t:f_t[0]):
                ot_secs = secs[0] - WEEK_OVERTIME_SECS
                if ot_secs > 0:
                    total[4] += ot_secs
                    wot_lst.append( (widx, self.get_str_time(ot_secs)) )
            
            total[1] -= total[4]
            total[2] = total[3] + total[4]
            
            data.append( [user_id, users_lku.get(user_id, 'UNK')] + map(self.get_str_time, total) + [wot_lst] )
            
        data.sort(key=lambda x: (x[1], x[0]))
        
        return data
    
    def fn_get_users(self):
        cur_ts = self.get_day_ts()
        frm_ts = self.get_day_ts(self.req.qsv_int('frm_ts') or cur_ts)
        to_ts = self.get_day_ts(self.req.qsv_int('to_ts') or cur_ts) + DAY_SECS
        
        self.req.writejs(self.get_users_stat(frm_ts, to_ts))


    def fn_user_report(self):
        user_id = self.qsv_int('user_id')
        frm_ts = self.req.qsv_int('frm_ts')
        to_ts = self.req.qsv_int('to_ts')
        
        cur = self.cur()
        cur.execute('select c.user_id,u.user_name from clockin_user c left join user u on (c.user_id=u.user_id) order by u.user_name asc')
        nzs = cur.column_names
        users = []
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            users.append(r)
        
        r = {'clockin_users': users, 'user_id': user_id, 'frm_ts': frm_ts, 'to_ts': to_ts}
        self.req.writefile('clockin_v2_user_report.html', r)
    

    def get_str_time(self, secs):
        #hrs,mins = divmod(secs / 60, 60)
        #return '%02d:%02d' % (hrs, mins)
        return '%0.2f' % (secs / 3600.0, )
    
    def fn_get_user_hists(self):
        user_id = self.qsv_int('user_id')
        cur_ts = self.get_day_ts()
        frm_ts = self.get_day_ts(self.qsv_int('ts') or cur_ts)
        to_ts = frm_ts + DAY_SECS
        
        data = []
        cur = self.cur()
        cur.execute('select in_ts,out_ts,memo,flag,id from clockin_hist where user_id=%s and (in_ts>=%s and in_ts<%s or out_ts>%s and out_ts<=%s or in_ts<%s and out_ts>%s) order by in_ts asc, out_ts asc, id asc', (
            user_id, frm_ts, to_ts, frm_ts, to_ts, frm_ts, to_ts
            )
        )
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            r['hrs'] = self.get_str_time( max(r['out_ts'] - r['in_ts'], 0) ),
            r['in_ts'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(r['in_ts']))
            r['out_ts'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(r['out_ts']))
            
            r['status'] = int(bool(r['flag'] & HIST_FLAG_STATUS))
            r['type'] = int(bool(r['flag'] & HIST_FLAG_TYPE))
            
            data.append(r)
            
        self.req.writejs(data)
    
    def fn_set_user_hist(self):
        hist_id = self.req.psv_int('hist_id')
        user_id = self.req.psv_int('user_id')
        in_time = self.req.psv_ustr('in_time')
        out_time = self.req.psv_ustr('out_time')
        memo = self.req.psv_ustr('memo')[:120].strip()
        status = self.req.psv_int('status')
        
        try:
            in_ts = int(time.mktime(time.strptime(in_time, '%m/%d/%Y %I:%M:%S %p')))
            out_ts = int(time.mktime(time.strptime(out_time, '%m/%d/%Y %I:%M:%S %p')))
        except Exception:
            self.req.exitjs({'err': 'error date input'})
        
        cur = self.cur()
        cur.execute('select count(*) from user where user_id=%s', (user_id,))
        if not cur.fetchall()[0][0]: self.req.exitjs({'err': 'user not exists'})
        
        h_type = HIST_FLAG_TYPE
        if hist_id:
            cur.execute('select flag from clockin_hist where id=%s', (hist_id,))
            rows = cur.fetchall()
            if not rows: self.req.exitjs({'err': 'history not exists'})
            h_type = rows[0][0] & HIST_FLAG_TYPE
        
        if h_type:
            if in_ts >= out_ts or self.get_day_ts(in_ts) != self.get_day_ts(out_ts - 1): self.req.exitjs({'err': 'error date range'})
            
        if not status:
            cur.execute('select count(*) from clockin_hist where user_id=%s and id!=%s and flag&'+str(HIST_FLAG_STATUS)+'=0 and (in_ts>=%s and in_ts<%s or out_ts>%s and out_ts<=%s or in_ts<%s and out_ts>%s)', (
                user_id, hist_id, in_ts, out_ts, in_ts, out_ts, in_ts, out_ts
                )
            )
            if cur.fetchall()[0][0]: self.req.exitjs({'err': 'date range overlapped'})
            
        if hist_id:
            s_flag = (status and 'flag=flag|%d' or 'flag=flag&~%d') % (HIST_FLAG_STATUS, )
            if h_type:
                cur.execute('update clockin_hist set in_ts=%s,out_ts=%s,memo=%s,'+s_flag+' where id=%s', (
                    in_ts, out_ts, memo, hist_id
                    )
                )
            else:
                cur.execute('update clockin_hist set memo=%s,'+s_flag+' where id=%s', (
                    memo, hist_id
                    )
                )
        else:
            flag = (status and HIST_FLAG_STATUS or 0) | HIST_FLAG_TYPE
            cur.execute('insert into clockin_hist values(null,%s,%s,%s,%s,%s)', (
                    user_id, in_ts, out_ts, memo, flag
                )
            )
            hist_id = cur.lastrowid
        
        self.req.writejs({'hist_id': hist_id})
        
        
    def fn_get_user_hist(self):
        hist_id = self.qsv_int('hist_id')
        
        cur = self.cur()
        cur.execute('select * from clockin_hist where id=%s', (hist_id,))
        rows = cur.fetchall()
        if not rows: return
        nzs = cur.column_names
        row = dict(zip(nzs, rows[0]))
        
        row['in_ts'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(row['in_ts']))
        row['out_ts'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(row['out_ts']))
        row['status'] = int(bool(row['flag'] & HIST_FLAG_STATUS))
        row['type'] = int(bool(row['flag'] & HIST_FLAG_TYPE))
        
        self.req.writejs(row)
    
    def get_user_hist_stat(self, frm_ts, to_ts, user_id=None):
        users = {}
        
        s_user = user_id and ' and user_id=%d' % (user_id) or ''
        cur = self.cur()
        cur.execute('select user_id,in_ts,out_ts from clockin_hist where flag&'+str(HIST_FLAG_STATUS)+'=0 and (in_ts>=%s and in_ts<%s or out_ts>%s and out_ts<=%s or in_ts<%s and out_ts>%s)'+s_user+' order by in_ts asc', (
            frm_ts, to_ts, frm_ts, to_ts, frm_ts, to_ts
            )
        )
        for r in cur.fetchall():
            user_id,in_ts,out_ts = r
            in_ts = max(in_ts, frm_ts)
            out_ts = min(out_ts, to_ts)
            
            days = users.setdefault(user_id, {})
            while(in_ts < out_ts):
                start_ts_day = self.get_day_ts(in_ts)
                end_ts_day = start_ts_day + DAY_SECS
                
                stat = days.setdefault(start_ts_day, [in_ts, 0, 0, 0, []])
                
                in_ts_day = max(in_ts, stat[1])
                out_ts_day = min(out_ts, end_ts_day)
                
                stat[3] += 1
                stat[4].append( (in_ts_day, out_ts_day) )
                if in_ts_day < out_ts_day:
                    stat[1] = out_ts_day
                    stat[2] += out_ts_day - in_ts_day
                
                in_ts = out_ts_day
        
        return users
    
    
    def get_user_report(self, user_id, frm_ts, to_ts):
        fw_ts = int(time.mktime(datetime.date(*WEEK_START_DAY).timetuple()))
        days = self.get_user_hist_stat(frm_ts, to_ts, user_id).get(user_id, {})
        
        data = []
        total = [0, 0, 0, 0, 0]
        week_overtime = {}
        for ts_day,stat in sorted(days.items(), key=lambda f_x: f_x[0]):
            first_in_ts,last_out_ts,total_secs,count,hists = stat[:5]
            normal_secs = min(total_secs, DAY_OVERTIME_SECS)
            overtime_secs = max(total_secs - DAY_OVERTIME_SECS, 0)
            total[0] += total_secs
            total[1] += normal_secs
            total[3] += overtime_secs
            if ts_day >= fw_ts: week_overtime.setdefault(int((ts_day - fw_ts)/WEEK_SECS), [0])[0] += normal_secs
            
            s_hists = []
            for hist in hists:
                s_hists.append(
                    (
                        time.strftime("%I:%M:%S %p", time.localtime(hist[0])),
                        time.strftime("%I:%M:%S %p", time.localtime(hist[1])),
                        self.get_str_time(max(0, hist[1] - hist[0]))
                    )
                )
            
            data.append((
                time.strftime("%m/%d/%Y", time.localtime(ts_day)),
                count,
                time.strftime("%I:%M:%S %p", time.localtime(first_in_ts)),
                time.strftime("%I:%M:%S %p", time.localtime(last_out_ts)),
                self.get_str_time(total_secs),
                self.get_str_time(normal_secs),
                self.get_str_time(overtime_secs),
                ts_day,
                s_hists
            ))
        
        wot_lst = []
        for widx,secs in sorted(week_overtime.items(), key=lambda f_t:f_t[0]):
            ot_secs = secs[0] - WEEK_OVERTIME_SECS
            if ot_secs > 0:
                total[4] += ot_secs
                wot_lst.append( (widx, self.get_str_time(ot_secs)) )
            
        total[1] -= total[4]
        total[2] = total[3] + total[4]

        return {'lst':data, 'ttl':map(self.get_str_time, total), 'wot': wot_lst}
    
    def fn_get_user_report(self):
        user_id = self.qsv_int('user_id')
        cur_ts = self.get_day_ts()
        frm_ts = self.get_day_ts(self.req.qsv_int('frm_ts') or cur_ts)
        to_ts = self.get_day_ts(self.req.qsv_int('to_ts') or cur_ts) + DAY_SECS
        
        self.req.writejs(self.get_user_report(user_id, frm_ts, to_ts))
        
    def fn_add_new_user(self):
        user_name = self.req.psv_ustr('user_name')[:64].strip().lower()
        if not user_name: return
        
        cur = self.cur()
        cur.execute('select count(*) from user where user_name=%s', (user_name,))
        if cur.fetchall()[0][0] > 0: self.req.exitjs({'err':'user exists'})
        
        dpw = self.genpasswd( str(random.random()) )
        cur.execute("insert into user values (0,%s,%s,0,0,0)", (user_name, dpw))
        self.req.writejs({'ret': cur.lastrowid})
        
    def fn_export_csv(self):
        js = self.req.psv_js('js')
        frm_ts = int(js['frm_ts'])
        to_ts = int(js['to_ts'])
        
        cur_ts = self.get_day_ts()
        frm_ts = self.get_day_ts(frm_ts or cur_ts)
        to_ts = self.get_day_ts(to_ts or cur_ts) + DAY_SECS
        
        if js['type'] == 'users':
            self.export_users(frm_ts, to_ts)
        elif js['type'] == 'user':
            self.export_user(int(js['user_id']), frm_ts, to_ts)

    def export_user(self, user_id, frm_ts, to_ts):
        js = self.get_user_report(user_id, frm_ts, to_ts)
        
        fp = cStringIO.StringIO()
        wt = csv.writer(fp)
        wt.writerow(['Day', 'Count', 'FirstInTime', 'LastOutTime', 'Total', 'Normal', 'Overtime'])
        for r in js['lst']:
            wt.writerow( [' ' + str(f_x) for f_x in r[:7]] )
            if len(r[-1]) > 1:
                for h in r[-1]: wt.writerow( ['-', ''] + [' ' + f_x for f_x in h] + ['', ''] )
            wt.writerow( ['', '', '', '', '', '', ''] )
        wt.writerow(['Total', '', '', ''] + [' ' + f_x for f_x in js['ttl']] )
        
        self.req.out_headers['content-type'] = 'application/octet-stream'
        self.req.out_headers['content-disposition'] = 'attachment; filename="data.csv"'
        self.req.write( fp.getvalue() )

    def export_users(self, frm_ts, to_ts):
        data = self.get_users_stat(frm_ts, to_ts)
        
        fp = cStringIO.StringIO()
        wt = csv.writer(fp)
        wt.writerow(['Name', 'Total', 'Normal', 'Overtime', 'DailyOT', 'WeeklyOT'])
        for r in data: wt.writerow( [' ' + f_x for f_x in r[1:7]] )
        
        self.req.out_headers['content-type'] = 'application/octet-stream'
        self.req.out_headers['content-disposition'] = 'attachment; filename="data.csv"'
        self.req.write( fp.getvalue() )
    
