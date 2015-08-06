import json
import time
import datetime
import config
import cPickle

CFG = {
    'id': 'CYCLE_COUNT_AF5643BB',
    'name': 'Cycle Count',
    'perm_list': [
    ('access', ''),
    ('admin', ''),
    ]
}

PERM_ADMIN = 1 << 1

class RequestHandler(App.load('/basehandler').RequestHandler):
    def fn_default(self):
        tabs = [] #[('user', 'User')]
        if self.get_cur_rh_perm() & PERM_ADMIN: tabs.extend( [
            {'id': 'manager', 'name': 'Manager'}, {'id': 'record', 'name': 'Record'}
            ] )

        r = {
            'tab_cur_idx' : 2,
            'title': 'Cycle Count',
            'tabs': tabs
        }
        self.req.writefile('tmpl_multitabs_v2.html', r)

    def fn_mobile(self):
        self.req.writefile('m_phy_count.html')


    def fn_manager(self):
        users = self.getuserlist()

    	self.req.writefile('cycle_count/manager.html', {'users': users, 'store_id': config.store_id})

    fn_manager.PERM = PERM_ADMIN


    def fn_record(self):
        r = {
            'r_id': self.req.qsv_int('r_id'),

        }
        self.req.writefile('cycle_count/record.html', r)

    fn_record.PERM = PERM_ADMIN


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
        cur.execute('delete from phycount_record where r_id=%s and qbpos_id=0', (r_id, ))
        rc = cur.rowcount
        if rc:
            cur.execute('delete from phycount_user where r_id=%s', (r_id, ))
            cur.execute('delete from phycount_user_hist where r_id=%s', (r_id, ))

        self.req.writejs({'err': int(rc <= 0)})

    fn_del_record.PERM = PERM_ADMIN



    def fn_upload_items_list(self):
        store_id = self.req.psv_int('store_id')
        items_list = self.req.psv_str('items_list')
 
        d_lst = {}
        for l in items_list.strip().split('\n'):
            num, name = l.strip().split(',')[:2]
            num = int(num.strip())
            name = name.strip()
            d_lst.setdefault(name, set()).add(num)

        nums = set()
        for v in d_lst.values(): nums.update(v)

        if not nums: return

        cur = self.cur()
        cur.execute('select num,sid from sync_items where num in (%s)' % ( ','.join(map(str, nums)) ))
        sids_lku = dict(cur.fetchall())

        r_ids = []
        for r_desc, nums in sorted(d_lst.items(), key=lambda f_x: f_x[0]):
            nums = sorted(nums)
            r_items = [ str(sids_lku[n]) for n in nums if sids_lku.has_key(n) ]
            if not r_items: continue

            r_id = 0
            r_loc = ''
            r_enable = 0
            r_mode = 1
            r_store = config.store_id - 1
            r_users = [1]
            r_js = {'r_items': r_items}

            r_id = self._save_record(r_id, r_desc, r_loc, r_enable, r_mode, r_store, r_items, r_users, r_js)
            r_ids.append(r_id)

        self.req.writejs({'r_ids': r_ids})

    fn_upload_items_list.PERM = PERM_ADMIN


    def _save_record(self, r_id, r_desc, r_loc, r_enable, r_mode, r_store, r_items, r_users, r_js):
        cts = int(time.time())

        cur = self.cur()
        if not r_id:
            cur.execute('insert into phycount_record values(null, 1, 0, %s, %s, %s, %s, %s, %s, %s)', (
                r_enable, r_mode, r_store, r_desc, r_loc, json.dumps(r_js, separators=(',',':')), cts
                )
            )
            if not cur.rowcount: return
            r_id = cur.lastrowid
        else:
            cur.execute('update phycount_record set r_rev=r_rev+1,r_enable=%s,r_desc=%s,r_loc=%s,r_js=%s where r_id=%s and qbpos_id=0', (
                r_enable, r_desc, r_loc, json.dumps(r_js, separators=(',',':')), r_id
                )
            )
            if not cur.rowcount: return
            cur.execute('delete from phycount_user where r_id=%d and u_uid not in (%s)' % (r_id, ','.join(map(str, r_users))) )
            if r_items:
                cur.execute('delete from phycount_item where r_id=%d and r_sid not in (%s)' % (r_id, ','.join(r_items)) )
            else:
                cur.execute('delete from phycount_item where r_id=%d')

        cur.executemany('insert ignore into phycount_user values(%s,%s)', [ (r_id, f_x) for f_x in r_users ] )
        if r_items: cur.executemany('insert ignore into phycount_item values(%s,%s)', [ (r_id, f_x) for f_x in r_items ] )

        return r_id


    def fn_save_record(self):
        js = self.req.psv_js('js')

        r_id = int(js.get('r_id') or 0)
        r_desc = js['r_desc'][:256].strip()
        r_loc = js['r_loc'][:256].strip()
        r_enable = int(js['r_enable'])
        r_mode = int(js['r_mode']) & 1
        
        #r_store = int(js['r_store']) & 1
        r_store = config.store_id - 1

        r_users = [ int(f_x) for f_x in js['r_users'] if f_x ]
        if not r_desc or not r_users: return

        if r_mode:
            r_items = map(str, set([ int(f_x) for f_x in js['r_items'] ]))
        else:
            r_items = []
        r_js = {'r_items': r_items}

        locs = set()
        for s in r_loc.replace('\n', ',').split(','):
            s = s.strip().lower()
            if not s: continue
            locs.add(s)
        r_loc = ','.join(sorted(locs))

        r_id = self._save_record(r_id, r_desc, r_loc, r_enable, r_mode, r_store, r_items, r_users, r_js)

        self.req.writejs({'r_id': r_id})

    fn_save_record.PERM = PERM_ADMIN


    def fn_load_record(self):
        r_id = self.req.qsv_int('r_id')

        cur = self.cur()
        cur.execute('select * from phycount_record where r_id=%s', (r_id, ))
        rows = cur.fetchall()
        if not rows: return
        r = dict(zip(cur.column_names, rows[0]))

        r_js = r['r_js'] = r['r_js'] and json.loads(r['r_js']) or {}
        r['items'] = r['r_js'].get('r_items')
        r_js['r_items'] = None

        d_users = dict([f_v[:2] for f_v in self.getuserlist()])
        cur.execute('select u_uid from phycount_user where r_id=%s', (r_id, ))
        r['r_users'] = dict([ (f_x[0], d_users.get(f_x[0], 'UNK')) for f_x in cur.fetchall() ])

        self.req.writejs(r)

    fn_load_record.PERM = PERM_ADMIN


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
            cur.execute('select r_id,r_store,r_mode,r_enable,q.doc_num,r_desc,(select GROUP_CONCAT(u_uid) from phycount_user where r_id=r.r_id),r_ts,qbpos_id from phycount_record r left join qbpos q on (r.qbpos_id=q.id) order by r_id desc limit %d,%d' % (
                        sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                if r[8]:
                    s = r[4] or '*'
                else:
                    s = ''

                r = list(r)
                r[3] = r[3] and 'Y' or 'N'
                r[1] = r[1] and 'SF' or 'SSF'
                r[2] = r[2] and 'Specific' or 'All'
                r[4] = s
                r[6] = ','.join([ d_users.get(int(f_x), 'UNK') for f_x in r[6].split(',') if f_x ])
                r[7] = time.strftime("%m/%d/%Y", time.localtime(r[7]))
                apg.append(r)
        
        cur.execute('select count(*) from phycount_record')
        rlen = int(cur.fetchall()[0][0])
        
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
    
    fn_get_records.PERM = PERM_ADMIN


    def fn_load_record_detail_by_user(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        u_id = self.req.qsv_int('u_id') or self.user_id
        if not(self.get_cur_rh_perm() & PERM_ADMIN): u_id = self.user_id

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
                cur_qty = h_js['cur_qty']
                fc = h_js['fc']

                apg.append((
                    num, name, str(h_qty) + (h_uom or ''), h_loc, time.strftime("%m/%d/%y %I:%M:%S %p", time.localtime(h_ts)), round(cur_qty / fc, 1) or '', '', str(h_sid)
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
        cur.execute('select r_id,r_desc,r_loc,r_ts from phycount_record where r_enable!=0 and qbpos_id=0 and r_id in (select r_id from phycount_user where u_uid=%d) order by r_id asc' % (self.user_id,))
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
            r['h_dt'] = time.strftime("%m/%d/%y %I:%M %p", time.localtime(r['h_ts']))

        self.req.writejs(ret)


    def fn_del_hist(self):
        h_id = self.req.psv_int('h_id')
        r_id = self.req.psv_int('r_id')

        cur = self.cur()
        cur.execute('delete from phycount_user_hist where h_id=%s and r_id=%s and u_id=%s and (select count(*) from phycount_record where r_enable!=0 and r_id=%s and qbpos_id=0)>0', (
            h_id, r_id, self.user_id, r_id
            )
        )
        self.req.writejs({'err': int(cur.rowcount <= 0)})


    def fn_save_qty(self):
        js = self.req.psv_js('js')
        h_sid = int(js['h_sid'])
        r_id = int(js['r_id'])

        cur = self.cur()
        cur.execute('select r.r_store,r.r_mode from phycount_user u left join phycount_record r on (u.r_id=r.r_id) where u.r_id=%s and u.u_uid=%s and r.r_enable!=0 and r.qbpos_id=0', (r_id, self.user_id))
        rows = cur.fetchall()
        if not rows: self.req.exitjs({'err': -1, 'err_s': 'No Record'})
        r_store,r_mode = rows[0]

        cts = int(time.time())

        if r_mode:
            cur.execute('select detail from sync_items where sid=%d and (select count(*) from phycount_item where r_id=%d and r_sid=%d) > 0' % (h_sid, r_id, h_sid))
        else:
            cur.execute('select detail from sync_items where sid=%s', (h_sid, ))
        rows = cur.fetchall()
        if not rows: self.req.exitjs({'err': -1, 'err_s': 'Item Not In List'})

        gjs = json.loads( rows[0][0] )
        cur_qty = gjs['stores'][r_store + 1][0]
        d_units = dict([ (u[2].lower(), u[3]) for u in gjs['units'] ])

        s = []
        for r in js['lst']:
            fc = d_units.get(r[1].lower()) or 0
            if fc <= 0: self.req.exitjs({'err': -100, 'err_s': 'Invalid Factor'})

            h_js = json.dumps({'fc': fc, 'cur_qty': cur_qty, 'base_uom': gjs['units'][0][2].lower()}, separators=(',',':'))
            s.append( (r_id, self.user_id, h_sid, int(r[0]), r[1], fc, js['loc'], cts, h_js) )

        if s: cur.executemany('insert into phycount_user_hist values(null,%s,%s,%s,%s,%s,%s,%s,%s,%s)', s)

        self.req.writejs({'err': int(not len(s))})


    def fn_get_count_items(self):
        r_id = self.req.qsv_int('r_id')
        diff_only = self.req.qsv_int('diff_only')

        if diff_only:
            record, d_user, d_item, items = self.count_cmp(r_id)
            i = d_user[ self.user_id ][1]
            items = [ (v[0], v[1], v[2][i], str(v[5]), d_item[v[5]][2]['deptname'] ) for v in items ]

        else:
            d_item = self.count_lst(r_id)
            items = d_item.values()
        
        items.sort(key=lambda f_k: f_k[0])
        self.req.writejs({'items': items})


    def count_lst(self, r_id):
        cur = self.cur()
        cur.execute('select * from phycount_record where r_id=%s', (r_id,))
        record = dict(zip(cur.column_names, cur.fetchall()[0]))

        cur.execute("select cval from configv2 where ckey='departments' limit 1")
        DEPTS = dict((f_x[1], f_x[0]) for f_x in cPickle.loads( cur.fetchall()[0][0] ))

        d_item = {}
        if record['r_mode']:
            cur.execute('select sid,num,name,deptsid from sync_items where sid in (select distinct r_sid from phycount_item where r_id=%d)' % (r_id,))
        else:
            cur.execute('select sid,num,name,deptsid from sync_items where sid in (select distinct h_sid from phycount_user_hist where r_id=%d)' % (r_id,))
        for r in cur.fetchall():
            sid,num,name,deptsid = r
            d_item.setdefault(sid, [num, name, None, str(sid), DEPTS.get(deptsid)])

        cur.execute('select h_sid,sum(h_qty * h_fc) from phycount_user_hist where r_id=%s and u_id=%s group by h_sid', (r_id, self.user_id))
        for r in cur.fetchall(): d_item[ r[0] ][2] = r[1]

        return d_item

    def count_cmp(self, r_id):
        cur = self.cur()
        cur.execute('select * from phycount_record where r_id=%s', (r_id,))
        record = dict(zip(cur.column_names, cur.fetchall()[0]))

        d_user = {}
        cur.execute('select u_uid,(select user_name from user where user_id=u_uid) as u_name from phycount_user where r_id=%s order by u_uid asc', (r_id,))
        k = 0
        for r in cur.fetchall():
            d_user[ r[0] ] = (r[1], k)
            k += 1

        cur.execute("select cval from configv2 where ckey='departments' limit 1")
        DEPTS = dict((f_x[1], f_x[0]) for f_x in cPickle.loads( cur.fetchall()[0][0] ))

        d_item = {}
        if record['r_mode']:
            cur.execute('select sid,num,name,detail,deptsid from sync_items where sid in (select distinct r_sid from phycount_item where r_id=%d)' % (r_id,))
        else:
            cur.execute('select sid,num,name,detail,deptsid from sync_items where sid in (select distinct h_sid from phycount_user_hist where r_id=%d)' % (r_id,))
        for r in cur.fetchall():
            sid,num,name,detail,deptsid = r
            gjs = json.loads(detail)
            gjs['deptname'] = DEPTS.get(deptsid)
            gjs['d_units'] = dict([ (u[2].lower(), u[3]) for u in gjs['units'] ])
            d_item.setdefault(sid, [num, name, gjs, [None,] * k, [[] for i in range(k)], [None, ] * k, True])

        cur.execute('select * from phycount_user_hist where r_id=%s order by h_id asc', (r_id,))
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))

            t = d_item.get( r['h_sid'] )
            if t == None: continue

            u = d_user.get( r['u_id'] )
            if u == None: continue

            h_js = json.loads(r['h_js'])

            in_qty = r['h_qty'] * h_js['fc']

            gjs = t[2]

            if gjs['d_units'].get(r['h_uom'].lower()) != h_js['fc']: t[6] = False
            if gjs['units'][0][2].lower() != h_js['base_uom']: t[6] = False

            if t[3][ u[1] ] != None:
                t[3][ u[1] ] += in_qty
            else:
                t[3][ u[1] ] = in_qty
            t[4][ u[1] ].append( (r['h_qty'], r['h_uom']) )
            t[5][ u[1] ] = h_js['cur_qty']

        items = []
        for sid,v in d_item.items():
            e = True
            if v[6] and v[3][0] != None:
                f = (v[3][0], v[5][0])
                a = 1
                while a < k:
                    if f != (v[3][a], v[5][a]):
                        e = False
                        break
                    a += 1
            else:
                e = False

            if not e: items.append( (v[0], v[1], v[3], v[4], v[5], sid, v[2]['units'][0][1]) )

        return (record, d_user, d_item, items)


    def fn_cmp(self):
        r_id = self.req.qsv_int('r_id')
        record, d_user, d_item, items = self.count_cmp(r_id)

        if not self.req.qsv_int('diff_only'):
            items = [ (v[0], v[1], v[3], v[4], v[5], str(f_sid), v[2]['units'][0][1]) for f_sid,v in d_item.items() ]
        else:
            _items = []
            for x in items:
                x = list(x)
                x[5] = str(x[5])
                _items.append(x)
            items = _items

        items.sort(key=lambda f_k: f_k[0])

        users = d_user.values()
        users.sort(key=lambda f_k: f_k[1])

        usr_idx = None
        d_usr_qty = None
        if record['qbpos_id']:
            cur = self.cur()
            cur.execute('select * from qbpos where id=%s', (record['qbpos_id'],))
            qbr = dict(zip(cur.column_names, cur.fetchall()[0]))
            if qbr['state'] == 2 and qbr['errno'] == 0 and qbr['doc_num']:
                ojs = json.loads(qbr['js']).get('ojs')
                if ojs:
                    usr_idx = ojs['idx']
                    o_d_item = ojs['items']
                    d_usr_qty = {}
                    for sid,v in o_d_item.items(): d_usr_qty[ str(sid) ] = v[-1]

        self.req.writejs({'items': items, 'users': users, 'ttl_num': len(d_item), 'd_usr_qty': d_usr_qty, 'usr_idx': usr_idx})

    def fn_send(self):
        r_id = self.req.psv_int('r_id')
        user_id = self.req.psv_int('user_id')
        record, d_user, d_item, items = self.count_cmp(r_id)

        if record['r_store'] + 1 != config.store_id: self.req.exitjs({'err': 1, 'err_s': 'Only Allow Store %d' % (config.store_id,)})
        if not d_item: self.req.exitjs({'err': 1, 'err_s': 'No Item'})

        idx = 0
        if items:
            if user_id:
                idx = d_user.get(user_id)[1]
                for sid,v in d_item.items():
                    if v[3][idx] == None:
                        self.req.exitjs({'err': 1, 'err_s': 'Not All Items Counted'})

            else:
                self.req.exitjs({'ret': 1, 'd_user': d_user})

        cur = self.cur()

        rev = record['r_rev']
        qbpos_id = record['qbpos_id']

        if not qbpos_id:
            cur.execute("insert into qbpos values(null,1,2,-99,%s,%s,null,0,null)", (4,r_id,))
            last_qbpos_id = cur.lastrowid
            cur.execute("update phycount_record set r_rev=r_rev+1,qbpos_id=%s where r_id=%s and r_rev=%s and qbpos_id=0", (
                last_qbpos_id, r_id, rev
                )
            )
            if cur.rowcount <= 0: self.req.exitjs({'err': -1, 'err_s': "can't send(1)"})
            qbpos_id = last_qbpos_id

        js = json.dumps({'items': d_item, 'd_user': d_user, 'store': record['r_store'], 'idx': idx}, separators=(',',':'))
        cur.execute("update qbpos set rev=rev+1,state=1,errno=0,js=%s where id=%s and state=2 and errno!=0", (js, qbpos_id,))
        if cur.rowcount <= 0: self.req.exitjs({'err': -1, 'err_s': "can't send(2)"})

        self.req.writejs({'r_id': r_id})

    fn_send.PERM = PERM_ADMIN
