import json
import time
import datetime
import config


PERM_PURCHASING_MGR = 1 << config.USER_PERM_BIT['purchasing_mgr']

DEFAULT_PERM = (1 << config.USER_PERM_BIT['base access']) | (1 << config.USER_PERM_BIT['normal access'])
class RequestHandler(App.load('/basehandler').RequestHandler):
    def fn_default(self):
        tabs = [('user', 'User')]
        if self.user_lvl & PERM_PURCHASING_MGR: tabs.extend( [('manager', 'Manager'), ('record', 'Record', True)] )

        r = {
            'tab_cur_idx' : 2,
            'title': 'Cycle Count',
            'tabs': tabs
        }
        self.req.writefile('tmpl_multitabs.html', r)

    def fn_mobile(self):
        self.req.writefile('m_phy_count.html')


    def fn_manager(self):
        users = self.getuserlist()

    	self.req.writefile('cycle_count/manager.html', {'users': users})

    fn_manager.PERM = PERM_PURCHASING_MGR


    def fn_record(self):
        r = {
            'r_id': self.req.qsv_int('r_id'),

        }
        self.req.writefile('cycle_count/record.html', r)

    fn_record.PERM = PERM_PURCHASING_MGR


    def fn_user(self):
        records = []
        cur = self.cur()
        cur.execute('select r_id,r_desc,r_ts from phycount_record where r_enable!=0 and r_id in (select r_id from phycount_user where u_uid=%d) order by r_id asc' % (self.user_id,))
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            records.append(r)

        self.req.writefile('cycle_count/user.html', {'records': records})

    def fn_del_record(self):
        r_id = self.req.psv_int('r_id')
        if not r_id: return

        cur = self.cur()
        cur.execute('delete from phycount_record where r_id=%s', (r_id, ))
        rc = cur.rowcount
        if rc:
            cur.execute('delete from phycount_user where r_id=%s', (r_id, ))
            cur.execute('delete from phycount_user_hist where r_id=%s', (r_id, ))

        self.req.writejs({'err': int(rc <= 0)})

    fn_del_record.PERM = PERM_PURCHASING_MGR

    def fn_save_record(self):
        r_id = self.req.psv_int('r_id')
        r_desc = self.req.psv_ustr('r_desc')[:256].strip()
        r_loc = self.req.psv_ustr('r_loc')[:256].strip()
        r_enable = self.req.psv_int('r_enable')
        r_users = [ int(f_x) for f_x in self.req.psv_ustr('r_users').split('|') if f_x ]
        if not r_desc or not r_users: return

        locs = set()
        for s in r_loc.replace('\n', ',').split(','):
            s = s.strip().lower()
            if not s: continue
            locs.add(s)
        r_loc = ','.join(sorted(locs))

        cts = int(time.time())

        cur = self.cur()
        if not r_id:
            cur.execute('insert into phycount_record values(null, 1, %s, %s, %s, null, %s)', (
                r_enable, r_desc, r_loc, cts
                )
            )
            if not cur.rowcount: return
            r_id = cur.lastrowid
        else:
            cur.execute('update phycount_record set r_rev=r_rev+1,r_enable=%s,r_desc=%s,r_loc=%s where r_id=%s', (r_enable, r_desc, r_loc, r_id))
            if not cur.rowcount: return
            cur.execute('delete from phycount_user where r_id=%d and u_uid not in (%s)' % (r_id, ','.join(map(str, r_users))) )
        
        cur.executemany('insert ignore into phycount_user values(%s,%s)', [ (r_id, f_x) for f_x in r_users ] )

        self.req.writejs({'r_id': r_id})

    fn_save_record.PERM = PERM_PURCHASING_MGR


    def fn_load_record(self):
        r_id = self.req.qsv_int('r_id')

        cur = self.cur()
        cur.execute('select * from phycount_record where r_id=%s', (r_id, ))
        rows = cur.fetchall()
        if not rows: return
        r = dict(zip(cur.column_names, rows[0]))

        d_users = dict([f_v[:2] for f_v in self.getuserlist()])
        cur.execute('select u_uid from phycount_user where r_id=%s', (r_id, ))
        r['r_users'] = dict([ (f_x[0], d_users.get(f_x[0], 'UNK')) for f_x in cur.fetchall() ])

        self.req.writejs(r)

    fn_load_record.PERM = PERM_PURCHASING_MGR


    def fn_get_records(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            d_users = dict([f_v[:2] for f_v in self.getuserlist()])
            cur.execute('select r_id,r_enable,r_desc,(select GROUP_CONCAT(u_uid) from phycount_user where r_id=r.r_id),r_ts from phycount_record r order by r_id desc limit %d,%d' % (
                        sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                r = list(r)
                r[1] = r[1] and 'Y' or 'N'
                r[3] = ','.join([ d_users.get(int(f_x), 'UNK') for f_x in r[3].split(',') if f_x ])
                r[4] = time.strftime("%m/%d/%Y", time.localtime(r[4]))
                apg.append(r)
        
        cur.execute('select count(*) from phycount_record')
        rlen = int(cur.fetchall()[0][0])
        
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
    
    fn_get_records.PERM = PERM_PURCHASING_MGR


    def fn_load_record_detail_by_user(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        u_id = self.req.qsv_int('u_id') or self.user_id
        if not(self.user_lvl & PERM_PURCHASING_MGR): u_id = self.user_id

        r_id = self.req.qsv_int('r_id')

        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select SQL_CALC_FOUND_ROWS h.h_sid,h.h_qty,h.h_uom,h.h_loc,h.h_ts,si.num,si.name,h.h_js from phycount_user_hist h left join sync_items si on(h.h_sid=si.sid) where h.u_id=%d and h.r_id=%d order by h.h_id desc limit %d,%d' % (
                        u_id, r_id, sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                h_sid,h_qty,h_uom,h_loc,h_ts,num,name,h_js = r
                h_js = json.loads(h_js)
                l_qs = h_js['l_qs']
                fc = h_js['fc']

                apg.append((
                    num, name, str(h_qty) + (h_uom or ''), h_loc, time.strftime("%m/%d/%y %I:%M:%S %p", time.localtime(h_ts)), round(l_qs[0] / fc, 1) or '', round(l_qs[1] / fc, 1) or '', str(h_sid)
                    )
                )

            cur.execute('select FOUND_ROWS()')
        else:
            cur.execute('select count(*) from phycount_user_hist where u_id=%d and r_id=%d' % (u_id, r_id))
        
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)


    def fn_load_cycle_count_list(self):
        ret = []
        cur = self.cur()
        cur.execute('select r_id,r_desc,r_loc,r_ts from phycount_record where r_enable!=0 and r_id in (select r_id from phycount_user where u_uid=%d) order by r_id asc' % (self.user_id,))
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            ret.append(r)
            r['r_dt'] = time.strftime("%m/%d/%y", time.localtime(r['r_ts']))

        self.req.writejs(ret)


    def fn_load_hist(self):
        h_sid = self.req.qsv_int('h_sid')
        r_id = self.req.qsv_int('r_id')

        ret = []
        cur = self.cur()
        cur.execute('select h_id,h_qty,h_uom,h_loc,h_ts from phycount_user_hist where h_sid=%s and r_id=%s and u_id=%s order by h_id desc', (
            h_sid, r_id, self.user_id
            )
        )
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            ret.append(r)
            r['h_dt'] = time.strftime("%m/%d/%y %I:%M:%S %p", time.localtime(r['h_ts']))

        self.req.writejs(ret)


    def fn_del_hist(self):
        h_id = self.req.psv_int('h_id')
        r_id = self.req.psv_int('r_id')

        cur = self.cur()
        cur.execute('delete from phycount_user_hist where h_id=%s and r_id=%s and u_id=%s and (select count(*) from phycount_record where r_enable!=0 and r_id=%s)>0', (
            h_id, r_id, self.user_id, r_id
            )
        )
        self.req.writejs({'err': int(cur.rowcount <= 0)})


    def fn_save_qty(self):
        js = self.req.psv_js('js')
        h_sid = int(js['h_sid'])
        r_id = int(js['r_id'])

        cur = self.cur()
        cur.execute('select count(*) from phycount_user where r_id=%s and u_uid=%s and (select count(*) from phycount_record where r_enable!=0 and r_id=%s)>0', (r_id, self.user_id, r_id))
        if cur.fetchall()[0][0] <= 0: return

        cts = int(time.time())

        cur.execute('select detail from sync_items where sid=%s', (h_sid, ))
        gjs = json.loads( cur.fetchall()[0][0] )
        d_units = dict([ (u[2].lower(), u[3]) for u in gjs['units'] ])
        l_qtys = gjs['qty']

        s = []
        for r in js['lst']:
            fc = d_units.get(r[1].lower()) or 0
            if fc <= 0: self.req.exitjs({'err': -100, 'err_s': 'Invalid Factor'})

            h_js = json.dumps({'l_qs': l_qtys, 'fc': fc})
            s.append( (r_id, self.user_id, h_sid, int(r[0]), r[1], js['loc'], cts, h_js) )

        if s: cur.executemany('insert into phycount_user_hist values(null,%s,%s,%s,%s,%s,%s,%s,%s)', s)

        self.req.writejs({'err': int(not len(s))})
