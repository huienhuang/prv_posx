import json
import time
import config
import datetime
import bisect


PROBLEMS = [
    'Other',
    'Missing Products',
    'Need To Call Customer(Deprecated)',
    'Out Of Stock',
    'Pick Wrong Products',
    'Customer Exchange',
    'Took Order Wrong',
    'Delivered Late'
]


DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        r = {}
        r['has_perm_admin'] = self.user_lvl & (1 << config.USER_PERM_BIT['admin'])
        self.req.writefile('delivery_v2.html', r)
    
    def fn_get_delivery_record(self):
        d_id = self.req.qsv_int('d_id')
        if not d_id: return
        
        cur = self.cur()
        cur.execute('select * from deliveryv2 where d_id=%s', (d_id,))
        rows = cur.fetchall()
        if not rows: self.req.exitjs({'msg': 'No Record ID #%s' % (d_id,)})
        dv = dict(zip(cur.column_names, rows[0]))
        js = json.loads(dv['js'])
        
        rec_lku = {}
        cur.execute('select dr.*,sr.sid,sr.sid_type,sr.cid,sr.global_js,(select count(*) from deliveryv2_receipt sdr where sdr.num=dr.num) as dup from deliveryv2_receipt dr left join sync_receipts sr on (dr.num=sr.num) where dr.d_id=%s', (d_id,))
        nzs = cur.column_names
        cids = set()
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            r['dup'] = r['dup'] > 1 and 1 or 0
            rec_lku[ r['num'] ] = r
            cids.add(r['cid'])
        
        for x in js:
            if x['type'] == 1:
                cids.add(x['cid'])
        
        cids.discard(None)
        cids_lku = {}
        if cids:
            cur.execute('select sid,name,detail from sync_customers where sid in (%s)' % (','.join(map(str,cids)),))
            for r in cur.fetchall():
                cust_gjs = r[2] and json.loads(r[2]) or {}
                cids_lku[ r[0] ] = {'company': r[1], 'terms': cust_gjs.get('udf5') or ''}
        
        msgs = []
        recs = []
        for l in js:
            r = None
            if l['type'] == 0:
                r = rec_lku.get(l['num'])
                if not r:
                    msgs.append('receipt#%d not exists' % (l['num'], ))
                    r = {}
                else:
                    r['inc'] = 1
            
                cid = r.get('cid')
                r['global_js'] = r.has_key('global_js') and json.loads(r['global_js']) or {}
                r['company'] = (r['global_js'].get('customer') or {}).get('company') or ''
                r['amount'] = r['global_js'].get('total') or 0
                r['global_js'] = ''
                r['sid'] = r.get('sid') != None and str(r['sid']) or ''
                r['cid'] = cid != None and str(cid) or ''
                l['js'] = r.get('js') != None and json.loads(r['js']) or {}
                if cid and cids_lku.has_key(cid): r['terms'] = cids_lku[cid]['terms']
                
            else:
                r = cids_lku.get(l['cid'])
                if not r:
                    msgs.append('customer#%d not exists' % (l['cid'], ))
                    r = {}
                l['payment_required'] = 1
                l['cid'] = str(l['cid'])
            
            r.update(l)
            recs.append(r)
        
        for num,r in rec_lku.items():
            if r.get('inc'): continue
            msgs.append('receipt#%d not included, out of sync' % (r['num'],))
        
        dv['js'] = ''
        dv['recs'] = recs
        dv['msg'] = '\n'.join(msgs)
        self.req.writejs(dv)
    
    
    def fn_get_delivery_record_list(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select d.d_id,d.name,u.user_name,d.count,d.ts from deliveryv2 d left join user u on (d.user_id=u.user_id) order by d.d_id desc limit %d,%d' % (
                        sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                r = list(r)
                r[3] = '%d/%d' % ((r[3] >> 16) & 0xFF, r[3] & 0xFF)
                r[4] = time.strftime("%m/%d/%Y", time.localtime(r[4]))
                apg.append(r)
        
        cur.execute('select count(*) from deliveryv2')
        rlen = int(cur.fetchall()[0][0])
        
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
    

    PAYMENTS = ('cash', 'check', 'card')
    def fn_delivery_edit(self):
        d_id = self.req.qsv_int('d_id')
        read_only = self.req.qsv_int('read_only')
        
        r = {
            'd_id': d_id,
            'read_only': read_only,
            'has_perm__accounting': self.user_lvl & (1 << config.USER_PERM_BIT['accounting'])
        }
        
        users = self.getuserlist()
        perm_driver = 1 << config.USER_PERM_BIT['driver']
        drivers = r['drivers'] = [ x for x in users if x[2] & perm_driver and x[0] != 1 ]
        drivers.insert(0, (0, '- Driver -', 0))
        
        perm_sales = 1 << config.USER_PERM_BIT['sales']
        sales = r['sales'] = [ x for x in users if x[2] & perm_sales and x[0] != 1 ]
        sales.insert(0, (0, '- Sales -', 0))
        
        r['printing_tmpls'] = ['For Driver', 'Accounting Report', 'Accounting Daily Report']
        r['payments'] = self.PAYMENTS
        r['problems'] = PROBLEMS
        
        self.req.writefile('delivery_edit_v2.html', r)


    def fn_get_delivery_receipt(self):
        num = self.req.qsv_ustr('num')
        if not num: self.req.exitjs({'err': 'error Num'})
        d_id = self.req.qsv_int('d_id')
        
        cur = self.cur()
        cur.execute('select sr.num,sr.cid,sr.sid,sr.sid_type,sr.global_js,sc.detail from sync_receipts sr left join sync_customers sc on (sc.sid=sr.cid) where sr.num=%s', (num,))
        rows = cur.fetchall()
        if not rows: self.req.exitjs({'err': 'No Such Receipt(%s)' % (num,)})
        r = dict(zip(cur.column_names, rows[0]))
        
        r['sid'] = str(r['sid'])
        r['cid'] = r['cid'] != None and str(r['cid']) or ''
        r['global_js'] = r['global_js'] and json.loads(r['global_js']) or {}
        r['company'] = (r['global_js'].get('customer') or {}).get('company') or ''
        r['amount'] = r['global_js']['total']
        r['global_js'] = ''
        
        r['detail'] = r['detail'] and json.loads(r['detail']) or {}
        r['terms'] = r['detail'].get('udf5') or ''
        r['detail'] = ''
        
        cur.execute('select count(*) from deliveryv2_receipt where num=%s and d_id!=%s', (num, d_id))
        r['dup'] = cur.fetchall()[0][0]
        
        self.req.writejs({'rec': r})

    def add_comment(self, rid, c_type, user_name, comment):
        cur = self.cur()
        cur.execute('insert into receipt_comment values (null,%s,%s,%s,%s,%s,%s)', (
            rid[0], rid[1], int(time.time()), c_type, user_name or self.user_name, comment
            )
        )

    def get_day_ts(self, ts):
        tp = time.localtime(ts or None)
        ts = int(time.mktime(datetime.date(tp.tm_year, tp.tm_mon, tp.tm_mday).timetuple()))
        return ts
    
    def fn_save_delivery_record(self):
        cur_ts = int(time.time())
        d_id = self.req.psv_int('d_id')
        rev = self.req.psv_int('rev')
        ts = cur_ts - self.get_day_ts(cur_ts) + self.get_day_ts(self.req.psv_int('ts'))
        name = self.req.psv_ustr('name')[:128].strip()
        recs = self.req.psv_js('recs')
        nums = [ int(x['num']) for x in recs if x.get('type') == 0 ]
        if len(nums) != len(set(nums)): self.req.exitjs({'err': 'duplicated receipt found'})
        
        users = self.getuserlist()
        users_lku = dict([x[:2] for x in users])
        
        cur = self.cur()
        
        orig_nums_lku = {}
        if d_id:
            cur.execute('select * from deliveryv2 where d_id=%s', (d_id,))
            rows = cur.fetchall()
            if not rows: self.req.exitjs({'err': 'No Record ID #%s' % (d_id,)})
            r = dict(zip(cur.column_names, rows[0]))
            if r['rev'] != rev: self.req.exitjs({'err': 'Revision Not Matched (%d, %d)' % (r['rev'], rev)})
            for n in json.loads(r['js']):
                if n['type'] == 0:
                    orig_nums_lku[ n['num'] ] = [False]
        
        nums_lku = {}
        if nums:
            cur.execute('select num,sid,sid_type from sync_receipts where num in (%s)' % (','.join(map(str,nums)),))
            for r in cur.fetchall(): nums_lku[ r[0] ] = r
        
        cids = [ int(x['cid']) for x in recs if x.get('type') == 1 ]
        cids_lku = {}
        if cids:
            cur.execute('select sid,name from sync_customers where sid in (%s)' % (','.join(map(str,cids)),))
            for r in cur.fetchall(): cids_lku[ r[0] ] = r
        
        err = []
        recs_db = []
        recs_js = []
        completed_count = 0
        for i in range( len(recs) ):
            rec = recs[i]
            r_type = rec.get('type')
            if r_type not in (0, 1): continue
            
            rec['num'] = int(rec.get('num') or 0)
            rec['changed'] = int(rec.get('changed') or 0)
            rec['driver_id'] = int(rec.get('driver_id') or 0)
            rec['delivered'] = int(bool(rec.get('delivered') or 0))
            rec['payment_required'] = int(bool(rec.get('payment_required') or 0))
            rec['js'] = rec.get('js') or {}
            
            if not rec['driver_id']:
                err.append('row#%d no driver assigned' % (i + 1,))
                continue
            
            usr_inst = rec['js'].get('inst') or {}
            
            pms = [ (int(p[0]), round(float(p[1]), 2), p[2][:128].strip() ) for p in rec['js'].get('payments') or [] ]
            pbs = {}
            problem_flag = 0
            for k,v in (rec['js'].get('problems') or {}).items():
                k = int(k)
                s = int(v[0])
                if not s: continue
                if k < 0 or k >= len(PROBLEMS): continue
                problem_flag |= 1 << k
                pbs[ str(k) ] = (s, v[1][:128].strip())
            rec['js'] = {'payments': pms, 'problems': pbs, 'note': rec['js'].get('note') or ''}
            rec['problem_flag'] = problem_flag
            
            inst_cash = float(usr_inst.get('cash') or 0)
            inst_check = float(usr_inst.get('check') or 0)
            if inst_cash or inst_check:
                rec['js']['inst'] = {
                    'cash': inst_cash,
                    'check': inst_check,
                    'check_no': (usr_inst.get('check_no') or '').strip(),
                    'contact': (usr_inst.get('contact') or '').strip(),
                    'memo': (usr_inst.get('memo') or '').strip(),
                }
            
            if r_type == 0:
                if rec['changed'] or not orig_nums_lku.has_key(rec['num']):
                    r = nums_lku.get(rec['num'])
                    if not r:
                        err.append('row#%d receipt#%d not exists' % (i + 1, rec['num']))
                        continue
                    else:
                        recs_db.append( (rec, r) )
                recs_js.append( {'type': 0, 'num': rec['num']} )
                orig_nums_lku.get(rec['num'], [False])[0] = True
                
                if rec['delivered'] and not pbs: completed_count += 1
                
            else:
                cid = int(rec.get('cid'))
                amount = round(float(rec.get('amount') or 0.0), 2)
                if rec['changed'] and not cids_lku.has_key(cid):
                    err.append('row#%d customer#%d not exists' % (i + 1, cid))
                    continue
                recs_js.append( {'type': 1, 'cid': cid, 'amount': amount, 'driver_id': rec['driver_id'], 'js': rec['js']} )
                
                if round(sum([ f_x[1] for f_x in pms ]), 2) >= amount and not pbs: completed_count += 1
                
        if err: self.req.exitjs({'err': '\n'.join(err)})
        
        
        if d_id:
            cur.execute('update deliveryv2 set rev=rev+1,count=%s,ts=%s,mts=%s,name=%s,js=%s where d_id=%s and rev=%s', (
                (completed_count << 16) | len(recs_js), ts, cur_ts, name, json.dumps(recs_js, separators=(',',':')), d_id, rev
                )
            )
            if cur.rowcount <= 0: self.req.exitjs({'err': 'Can Not Upate Record ID #%s' % (d_id,)})
        else:
            cur.execute('insert into deliveryv2 values (null,0,%s,%s,%s,%s,%s,%s)', (
                self.user_id, (completed_count << 16) | len(recs_js), ts, cur_ts, name, json.dumps(recs_js, separators=(',',':'))
                )
            )
            d_id = cur.lastrowid
            
        for rec,r in recs_db:
            s_js = json.dumps(rec['js'], separators=(',',':'))
            cur.execute('insert into deliveryv2_receipt values (%s,%s,%s,%s,%s,%s,%s,%s,%s) on duplicate key update driver_id=%s,delivered=%s,user_id=%s,payment_required=%s,problem_flag=%s,problem_flag_s=problem_flag_s|%s,js=%s', (
                d_id, rec['num'], rec['driver_id'], rec['delivered'], 0, rec['payment_required'], rec['problem_flag'], rec['problem_flag'], s_js,
                rec['driver_id'], rec['delivered'], 0, rec['payment_required'], rec['problem_flag'], rec['problem_flag'], s_js
                )
            )
            rc = cur.rowcount
            if rc > 0:
                self.add_comment((r[1], r[2]), 1, None, 'SetDelivery_V2 -> ID#%d Driver(%s) PRCV(%s) Delivered(%s) Problem(%s) PREQ(%s)' % (
                    d_id,
                    rec['driver_id'] and users_lku.get(rec['driver_id'], 'UNK') or '',
                    '%0.2f' % ( sum([x[1] for x in rec['js']['payments']]), ),
                    rec['delivered'] and 'Y' or 'N',
                    rec['problem_flag'] and 'Y' or 'N',
                    rec['payment_required'] and 'Y' or 'N',
                    )
                )
        
        ret = {}
        nums = [ str(x[0]) for x in orig_nums_lku.items() if not x[1][0] ]
        if nums:
            cur.execute('delete from deliveryv2_receipt where d_id=%s and num in (%s)' % (
                d_id, ','.join(nums)
                )
            )
        
        ret['d_id'] = d_id
        self.req.writejs(ret)


    def fn_delivery_printing_accounting_report(self):
        d_id = self.req.qsv_int('d_id')
        if not d_id: return
        
        dr = self.prepare_record_per_driver(d_id)
        dr['auto_print'] = 0
        self.req.writefile('delivery_printing_accounting_report_v2.html', dr)
        
    fn_delivery_printing_accounting_report.PERM = 1 << config.USER_PERM_BIT['accounting']

    def fn_delivery_printing_for_driver(self):
        d_id = self.req.qsv_int('d_id')
        if not d_id: return
        
        dr = self.prepare_record_per_driver(d_id)
        self.req.writefile('delivery_printing_for_driver_v2.html', dr)
    
    def prepare_record_per_driver(self, d_id):
        cur = self.cur()
        
        cur.execute('select *,(select user_name from user where user_id=d.user_id) as user_name from deliveryv2 d where d_id=%s', (d_id,))
        rows = cur.fetchall()
        if not rows: return
        dv = dict(zip(cur.column_names, rows[0]))
        js = json.loads(dv['js'])
        
        dr = {
            'd_name': dv['name'],
            'd_id': d_id,
            'd_date': time.strftime("%m/%d/%Y", time.localtime(dv['ts'])),
            'auto_print': self.req.qsv_int('auto_print'),
            'cur_driver_id': self.req.qsv_int('driver_id'),
            'user_name': dv['user_name']
        }
        users = self.getuserlist()
        users_lku = dr['users_lku'] = {}
        perm_driver = 1 << config.USER_PERM_BIT['driver']
        drivers = dr['drivers'] = []
        for x in users:
            users_lku[ x[0] ] = x[1]
            if x[2] & perm_driver and x[0] != 1: drivers.append(x)
        drivers.insert(0, (0, 'Select Driver', 0))
        
        
        rec_lku = {}
        cur.execute('select dr.*,sr.sid,sr.sid_type,sr.cid,sr.global_js from deliveryv2_receipt dr left join sync_receipts sr on (dr.num=sr.num) where dr.d_id=%s', (d_id,))
        nzs = cur.column_names
        cids = set()
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            rec_lku[ r['num'] ] = r
            cids.add(r['cid'])
        
        for x in js:
            if x['type'] == 1:
                cids.add(x['cid'])
        
        cids.discard(None)
        cids_lku = {}
        if cids:
            cur.execute('select sid,name,detail from sync_customers where sid in (%s)' % (','.join(map(str,cids)),))
            for r in cur.fetchall():
                cust_gjs = r[2] and json.loads(r[2]) or {}
                cids_lku[ r[0] ] = {'company': r[1], 'terms': cust_gjs.get('udf5') or ''}
        
        dr['payments'] = list(self.PAYMENTS[:]) + ['other']
        dr['overall_stat'] = overall_stat = [0,] * (len(self.PAYMENTS) + 1) * 2
        dr['drv_d'] = drv_d = {}
        for l in js:
            r = None
            if l['type'] == 0:
                r = rec_lku.get(l['num'])
                if not r: r = {}
                r['global_js'] = r.has_key('global_js') and json.loads(r['global_js']) or {}
                r['company'] = (r['global_js'].get('customer') or {}).get('company') or ''
                r['amount'] = r['global_js'].get('total') or 0
                l['js'] = r.get('js') != None and json.loads(r['js']) or {}
                
                cid = r.get('cid')
                if cid and cids_lku.has_key(cid): r['terms'] = cids_lku[cid]['terms']
                
            else:
                r = cids_lku.get(l['cid'])
                if not r: r = {}
                l['payment_required'] = 1
                l['cid'] = str(l['cid'])
        
            r.update(l)
            recs,stat = drv_d.setdefault(r.get('driver_id') or 0, ([], [0,] * (len(self.PAYMENTS) + 1) * 2))
            recs.append(r)
            
            pms = (r.get('js') or {}).get('payments') or []
            for p_type,p_amt,p_memo in pms:
                if p_type < 0 and p_type >= len(self.PAYMENTS): p_type = len(self.PAYMENTS)
                p_type *= 2
                overall_stat[p_type] += p_amt
                overall_stat[p_type + 1] += 1
                stat[p_type] += p_amt
                stat[p_type + 1] += 1
        
        return dr

    
    def prepare_record_per_driver_2(self, d_id):
        cur = self.cur()
        
        cur.execute('select ts from deliveryv2 where d_id=%s', (d_id,))
        rows = cur.fetchall()
        if not rows: return
        tp = time.localtime(rows[0][0])
        frm = int(time.mktime(datetime.date(tp.tm_year, tp.tm_mon, tp.tm_mday).timetuple()))
        to = frm + 3600 * 24
        
        cur.execute('select d_id,js from deliveryv2 where ts>=%s and ts<%s order by d_id', (frm, to))
        jss = []
        d_ids = []
        for r in cur.fetchall():
            jss.append( (r[0], json.loads(r[1])) )
            d_ids.append(r[0])
        
        dr = {
            'd_ids': d_ids,
            'auto_print': self.req.qsv_int('auto_print'),
            'd_date': time.strftime("%m/%d/%Y", tp),
        }
        
        users = self.getuserlist()
        users_lku = dr['users_lku'] = {}
        for x in users: users_lku[ x[0] ] = x[1]
        
        d_id_rec_lku = {}
        cur.execute('select dr.*,sr.sid,sr.sid_type,sr.cid,sr.global_js from deliveryv2_receipt dr left join sync_receipts sr on (dr.num=sr.num) where dr.d_id in (%s)' % (','.join(map(str, d_ids)),))
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            d_id_rec_lku.setdefault(r['d_id'], {})[ r['num'] ] = r
        
        dr['payments'] = list(self.PAYMENTS[:]) + ['other']
        dr['overall_stat'] = overall_stat = [0,] * (len(self.PAYMENTS) + 1) * 2
        dr['drv_d'] = drv_d = {}
        for d_id,js in jss:
            rec_lku = d_id_rec_lku.get(d_id, {})
            for l in js:
                r = {}
                if l['type'] == 0:
                    r = rec_lku.get(l['num'])
                    if not r: r = {}
                    r['global_js'] = r.has_key('global_js') and json.loads(r['global_js']) or {}
                    r['amount'] = r['global_js'].get('total') or 0
                    l['js'] = r.get('js') != None and json.loads(r['js']) or {}
                    
                r.update(l)
                recs,stat = drv_d.setdefault(r.get('driver_id') or 0, ([], [0,] * (len(self.PAYMENTS) + 1) * 2))
                recs.append(r)
                
                pms = (r.get('js') or {}).get('payments') or []
                for p_type,p_amt,p_memo in pms:
                    if p_type < 0 and p_type >= len(self.PAYMENTS): p_type = len(self.PAYMENTS)
                    p_type *= 2
                    overall_stat[p_type] += p_amt
                    overall_stat[p_type + 1] += 1
                    stat[p_type] += p_amt
                    stat[p_type + 1] += 1
        
        return dr


    def fn_delivery_printing_accounting_daily_report(self):
        d_id = self.req.qsv_int('d_id')
        if not d_id: return
        
        dr = self.prepare_record_per_driver_2(d_id)
        dr['auto_print'] = 0
        self.req.writefile('delivery_printing_accounting_daily_report_v2.html', dr)
        
    fn_delivery_printing_accounting_daily_report.PERM = 1 << config.USER_PERM_BIT['accounting']


    def fn_delete(self):
        d_id = self.req.psv_int('d_id')
        if not d_id: return
        
        cur = self.cur()
        cur.execute('delete from deliveryv2_receipt where d_id=%s', (d_id,))
        cur.execute('delete from deliveryv2 where d_id=%s', (d_id,))
        
        self.req.writejs({'d_id':d_id})
        
    fn_delete.PERM = 1 << config.USER_PERM_BIT['admin'] 

    def fn_get_problem_receipts(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            
            users = self.getuserlist()
            users_lku = dict([x[:2] for x in users])
        
            cur.execute('select SQL_CALC_FOUND_ROWS r.num,sr.global_js,d.user_id,r.driver_id,r.d_id,d.name,sr.order_date,d.ts,sr.sid,sr.sid_type from deliveryv2_receipt r left join sync_receipts sr on (sr.num=r.num) left join deliveryv2 d on (r.d_id=d.d_id) where d.d_id is not null and sr.num is not null and r.problem_flag!=0 order by r.num desc, r.d_id desc limit %d,%d' % (
                sidx * pgsz, (eidx - sidx) * pgsz
                )
            )
            
            for r in cur.fetchall():
                r = list(r)
                
                r[1] = r[1] and json.loads(r[1]) or {}
                r[1] = (r[1].get('customer') or {}).get('company') or ''
                r[2] = r[2] and users_lku.get(r[2], 'UNK') or ''
                r[3] = r[3] and users_lku.get(r[3], 'UNK') or ''
                r[6] = time.strftime("%m/%d/%y", time.localtime(r[6]))
                r[7] = time.strftime("%m/%d/%y", time.localtime(r[7]))
                r[8] = str(r[8])
                
                apg.append(r)
        
            cur.execute('select FOUND_ROWS()')
        
        else:
            cur.execute('select count(*) from deliveryv2_receipt r left join sync_receipts sr on (sr.num=r.num) left join deliveryv2 d on (r.d_id=d.d_id) where d.d_id is not null and sr.num is not null and r.problem_flag!=0')
            
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)

    def fn_report(self):
        self.req.writefile('delivery_v2_report.html')
        
    def _fn_get_report__delivery_pickup(self):
        m = self.req.qsv_int('m')
        
        year,month = divmod(m, 100)
        frm_ts = int(time.mktime(datetime.date(year, month, 1).timetuple()))
    
        month += 1
        if month > 12:
            month = 1
            year += 1
        to_ts = int(time.mktime(datetime.date(year, month, 1).timetuple()))
        
        cur = self.cur()
        cur.execute('select num,items_js from sync_receipts where num in (select distinct num from deliveryv2_receipt) and order_date >= %s and order_date < %s and type&0xFFFF=0', (
            frm_ts, to_ts
            )
        )
        
        cn_pickup = 0
        cn_line = 0
        cn_qty = 0
        rows = cur.fetchall()
        for row in rows:
            rec_in = False
            for item in json.loads(row[1]):
                if item['itemsid'] == 1000000005: continue
                if item['qty'] <= 0: continue
                rec_in = True
                
                cn_line += 1
                cn_qty += item['qty']
                
            if rec_in: cn_pickup += 1
            
        self.req.writejs(
            {
            'total': len(rows),
            'pickup': cn_pickup,
            'line': cn_line,
            'qty': cn_qty
            }
        )
        
    def fn_get_report__delivery_pickup(self):
        m = self.req.qsv_int('m')
        year,month = divmod(m, 100)
        frm_ts = int(time.mktime(datetime.date(year, month, 1).timetuple()))
        
        js = self.get_data_file_cached('delivery_report', 'delivery_report.txt')
        if not js: return
        
        mons = js['mons']
        idx = bisect.bisect_left([f_x[0] for f_x in mons], frm_ts)
        if idx >= len(mons) or mons[idx][0] != frm_ts: return
    
        data = mons[idx][1]
        ret = {
            'total': len(data['nums']),
            'line': data['lines'],
            'qty': data['qtys'],
            'sale': 0
        }
        
        js = self.get_data_file_cached('receipt_report', 'receipt_report.txt')
        if js:
            mons = js['summary']
            idx = bisect.bisect_left([f_x[0] for f_x in mons], frm_ts)
            if idx < len(mons) and mons[idx][0] == frm_ts: ret['sale'] = mons[idx][1][4]
        
        self.req.writejs(ret)
        
    fn_get_report__delivery_pickup.PERM = 1 << config.USER_PERM_BIT['admin']
    

    def fn_get_report__delivery_completed(self):
        ts = self.req.qsv_int('ts') or int(time.time())
        
        frm_ts = self.get_day_ts(ts)
        to_ts = frm_ts + 3600 * 24
        
        cur = self.cur()
        cur.execute('select count from deliveryv2 where ts>=%s and ts<%s', (
            frm_ts, to_ts
            )
        )
        count = [0, 0]
        for row in cur.fetchall():
            count[0] += row[0] & 0xFF
            count[1] += (row[0] >> 16) & 0xFF
            
        self.req.writejs(
            {
            'total': count[0],
            'completed': count[1],
            }
        )
        
    fn_get_report__delivery_completed.PERM = 1 << config.USER_PERM_BIT['admin']
    
    
    
    
    