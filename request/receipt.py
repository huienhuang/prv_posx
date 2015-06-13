import json
import time
import config
import datetime

CFG = {
    'id': 'RECEIPT_C00B8008',
    'name': 'Receipt',
    'perm_list': [
    ('access', ''),
    ('account report', ''),
    ]
}
PERM_ACC = 1 << 1

BIT_ACC = (1 << config.BASE_ROLES_MAP['Accounting'])
BIT_DRV = (1 << config.BASE_ROLES_MAP['Driver'])


REC_FLAG_DELIVERED = 1 << 0
REC_FLAG_PROBLEM = 1 << 1
REC_FLAG_PAID = 1 << 2
REC_FLAG_PM_REQ = 1 << 3

class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def add_comment(self, rid, c_type, user_name, comment):
        cur = self.cur()
        cur.execute('insert into receipt_comment values (null,%s,%s,%s,%s,%s,%s)', (
            rid[0], rid[1], int(time.time()), c_type, user_name or self.user_name, comment
            )
        )
    
    def fn_add_comment(self):
        sid = self.req.psv_int('sid')
        sid_type = self.req.psv_int('sid_type')
        if not sid: return
        
        comment = self.req.psv_ustr('comment')[:256].strip()
        if not comment: return
        
        cur = self.cur()
        
        cur.execute('select count(*) from sync_receipts where sid=%s and sid_type=0', (sid, sid_type))
        if cur.fetchall()[0][0] <= 0: return
        
        self.add_comment((sid, sid_type), 0, self.user_name, comment)
        
        self.req.writejs({'sid':sid, 'sid_type':sid_type})
    
    def set_shipping(self, receipt):
        driver_id = self.req.psv_int('shipping_driver_id')
    
        db = self.db()
        cur = db.cur()
        
        driver = None
        if driver_id: driver = self.finduser(driver_id)
        
        cur.execute("insert into receipt values (%s,%s,%s,%s,0,%s,'','{}') on duplicate key update driver_id=%s", (
                    receipt['sid'], receipt['sid_type'], 0, receipt['num'], driver_id,
                    driver_id
                    )
        )
        if cur.rowcount > 0:
            self.add_comment(
                (receipt['sid'], receipt['sid_type']),
                1,
                self.user_name,
                'SetShipping -> driver: %s(%d)' % (
                    driver and driver[1] or 'None', driver_id,
                    )
            )
        
        self.req.writejs({'ret':1})
    
    def set_delivered(self, receipt):
        delivered = int(bool(self.req.psv_int('delivered')))
        
        cur = self.cur()
        s_flag = (delivered and 'flag|%d' or 'flag&~%d') % (REC_FLAG_DELIVERED,)
        cur.execute("insert into receipt values (%s,%s,%s,%s,0,0,'','{}') on duplicate key update flag="+s_flag, (
                    receipt['sid'], receipt['sid_type'], delivered and REC_FLAG_DELIVERED or 0, receipt['num'],
                    )
        )
        if cur.rowcount > 0:
            self.add_comment(
                (receipt['sid'], receipt['sid_type']),
                1,
                self.user_name,
                'SetDelivered -> %s' % (delivered and 'YES' or 'NO')
            )
    
        self.req.writejs({'ret':1})
    
    def set_problem(self, receipt):
        problem = int(bool(self.req.psv_int('problem')))
        memo = problem and self.req.psv_ustr('problem_memo')[:256].strip() or ''
        
        cur = self.cur()
        s_flag = (problem and 'flag|%d' or 'flag&~%d') % (REC_FLAG_PROBLEM, )
        cur.execute("insert into receipt values (%s,%s,%s,%s,0,0,%s,'{}') on duplicate key update flag="+s_flag+",memo=%s", (
                    receipt['sid'], receipt['sid_type'], problem and REC_FLAG_PROBLEM or 0, receipt['num'], memo,
                    memo
            )
        )
        if cur.rowcount > 0:
            self.add_comment(
                (receipt['sid'], receipt['sid_type']),
                1,
                self.user_name,
                'SetProblem -> %s, %s' % (problem and 'YES' or 'NO', memo)
            )
    
        self.req.writejs({'ret':1})
    
    def fn_config(self):
        sid = self.req.psv_int('sid')
        sid_type = self.req.psv_int('sid_type')
        e_type = self.req.psv_ustr('type')
        
        db = self.db()
        cur = db.cur()
        
        cur.execute('select * from sync_receipts where sid=%s and sid_type=%s', (sid, sid_type))
        rows = cur.fetchall()
        if not rows: self.req.exitjs({'err':'no such receipt'})
        
        receipt = dict(zip(cur.column_names, rows[0]))
        
        if e_type == 'shipping': return self.set_shipping(receipt)
        elif e_type == 'delivered': return self.set_delivered(receipt)
        elif e_type == 'problem': return self.set_problem(receipt)
        
        self.req.exitjs({'err':'unexpected type'})
    
    
    def fn_delivery(self):
        self.req.writefile('delivery.html')
    
    def fn_delivery_edit(self):
        d_id = self.req.qsv_int('d_id')
        read_only = self.req.qsv_int('read_only')
        
        r = {
            'd_id': d_id,
            'read_only': read_only,
            'has_perm__accounting': self.user_roles() & BIT_ACC
        }
        
        users = self.get_user_roles()
        perm_driver = BIT_DRV
        drivers = r['drivers'] = [ x for x in users if x[2] & perm_driver and x[0] != 1 ]
        drivers.insert(0, (0, 'Select Driver', 0))
        
        payments = self.getconfigv2('payments')
        payments = r['payments'] = payments and json.loads(payments) or []
        payments.insert(0, (0, 'Select Payment'))
        
        r['printing_tmpls'] = ['For Driver', 'Accounting Report']
        
        self.req.writefile('delivery_edit.html', r)
    
    
    def prepare_record_per_driver(self, d_id):
        cur = self.cur()
        
        cur.execute('select * from delivery where id=%s', (d_id,))
        rows = cur.fetchall()
        if not rows: return
        r = dict(zip(cur.column_names, rows[0]))
        nums = json.loads(r['js'])
        
        dr = {
            'd_name': r['name'],
            'd_id': d_id,
            'd_date': time.strftime("%m/%d/%Y", time.localtime(r['ts'])),
            'auto_print': self.req.qsv_int('auto_print'),
            'cur_driver_id': self.req.qsv_int('driver_id')
        }
        users = self.get_user_roles()
        users_lku = dr['users_lku'] = {}
        perm_driver = BIT_DRV
        drivers = dr['drivers'] = []
        for x in users:
            users_lku[ x[0] ] = x[1]
            if x[2] & perm_driver and x[0] != 1:
                drivers.append(x)
        drivers.insert(0, (0, 'Select Driver', 0))
        
        payments = self.getconfigv2('payments')
        payments_lku = payments and dict(json.loads(payments)) or {}
        dr['payments_lku'] = payments_lku
        
        lku = {}
        if nums:
            cur.execute('select r.num,r.sid,r.sid_type,r.cid,r.global_js,rr.delivery_id,rr.driver_id,rr.flag,rr.memo,rr.js from sync_receipts r left join receipt rr on (r.sid=rr.sid and r.sid_type=rr.sid_type) where r.num in (%s)' % (','.join(map(str,nums)),))
            nzs = cur.column_names
            for x in cur.fetchall():
                x = dict(zip(nzs, x))
                lku[ x['num'] ] = x
                
                flag = x['flag'] or 0
                x['delivered'] = flag & REC_FLAG_DELIVERED
                x['problem'] = flag & REC_FLAG_PROBLEM
                x['payment_required'] = flag & REC_FLAG_PM_REQ
                
                gjs = json.loads(x['global_js'])
                x['company'] = (gjs.get('customer') or {}).get('company', '')
                x['js'] = json.loads(x['js'])
                x['amount'] = gjs['total']
        
        drvs_stat = [0, ([0,0], [0,0], [0,0], [0,0])]
        d_drivers = {}
        for num in nums:
            rec = lku.get(num)
            drvs_stat[0] += 1
            
            if not rec:
                d_drivers.setdefault(0, [[], ([0,0], [0,0], [0,0], [0,0])])[0].append( (num, None) )
                continue
            
            d_drv = d_drivers.setdefault(rec['driver_id'], [[], ([0,0], [0,0], [0,0], [0,0])])
            d_drv[0].append( (num, rec) )
            
            pm = rec['js'].get('payment')
            if not pm or not pm[0]: continue
            if pm[0] >= 1 and pm[0] <= 3:
                d_drv[1][ pm[0] ][0] += 1
                d_drv[1][ pm[0] ][1] += pm[1]
                drvs_stat[1][ pm[0] ][0] += 1
                drvs_stat[1][ pm[0] ][1] += pm[1]
            else:
                d_drv[1][0][0] += 1
                d_drv[1][0][1] += pm[1]
                drvs_stat[1][0][0] += 1
                drvs_stat[1][0][1] += pm[1]
            
        dr['d_drivers'] = sorted( d_drivers.items(), key=lambda x: x[0] )
        dr['drvs_stat'] = drvs_stat
        
        return dr
        
    def fn_delivery_printing_accounting_report(self):
        d_id = self.req.qsv_int('d_id')
        if not d_id: return
        
        dr = self.prepare_record_per_driver(d_id)
        self.req.writefile('delivery_printing_accounting_report.html', dr)
        
    fn_delivery_printing_accounting_report.PERM = PERM_ACC

    def fn_delivery_printing_for_driver(self):
        d_id = self.req.qsv_int('d_id')
        if not d_id: return
        
        dr = self.prepare_record_per_driver(d_id)
        self.req.writefile('delivery_printing_for_driver.html', dr)
    
    def make_rec(self, r):
        if not r:
            return {
                'cid': '',
                'num': 0,
                'delivery_id': 0,
                'driver_id': 0,
                'company': '',
                'amount': '',
                'delivered': 0,
                'problem': 0,
                'payment_required': 0,
                'memo': '',
                'sid': '',
                'sid_type': 0,
                'js': {}
            }
        
        gjs = json.loads(r['global_js'])
        flag = r['flag'] or 0
        return {
            'cid': r['cid'] and str(r['cid']) or '',
            'num': r['num'],
            'delivery_id': r['delivery_id'] or 0,
            'driver_id': r['driver_id'] or 0,
            'company': (gjs.get('customer') or {}).get('company', ''),
            'amount': gjs['total'],
            'delivered': int(bool(flag & REC_FLAG_DELIVERED)),
            'problem': int(bool(flag & REC_FLAG_PROBLEM)),
            'payment_required': int(bool(flag & REC_FLAG_PM_REQ)),
            'memo': r['memo'] or '',
            'sid': str(r['sid']),
            'sid_type': r['sid_type'],
            'js': r['js'] and json.loads(r['js']) or {},
        }
    
    def fn_get_delivery_record(self):
        d_id = self.req.qsv_int('d_id')
        if not d_id: return
        
        cur = self.cur()
        
        cur.execute('select * from delivery where id=%s', (d_id,))
        rows = cur.fetchall()
        if not rows: self.req.exitjs({'msg': 'No Record ID #%s' % (d_id,)})
        dr = dict(zip(cur.column_names, rows[0]))
        nums = json.loads(dr['js'])
        
        msgs = []
        recs = []
        lku = {}
        
        if nums:
            cur.execute('select r.num,r.sid,r.sid_type,r.cid,r.global_js,rr.delivery_id,rr.driver_id,rr.flag,rr.memo,rr.js from sync_receipts r left join receipt rr on (r.sid=rr.sid and r.sid_type=rr.sid_type) where r.num in (%s)' % (','.join(map(str,nums)),))
            nzs = cur.column_names
            for r in cur.fetchall(): lku[ r[0] ] = dict(zip(nzs, r))
            
        for i in range( len(nums) ):
            num = nums[i]
            r = lku.get(num)
            if not r:
                msgs.append('receipt#%d not exists' % (num, ))
            else:
                delivery_id =  r['delivery_id'] or 0
                if delivery_id != d_id:
                    msgs.append('receipt#%d assigned to another record#%d' % (num, delivery_id))
            
            rec = self.make_rec(r)
            if not r:
                rec['num'] = num
                rec['delivery_id'] = -1
            recs.append(rec)
        
        self.req.writejs({'recs': recs, 'd_id': d_id, 'rev': dr['rev'], 'ts': dr['ts'], 'name': dr['name'], 'msg': '\n'.join(msgs)})
    
    def fn_save_delivery_record(self):
        cur_ts = int(time.time())
        d_id = self.req.psv_int('d_id')
        rev = self.req.psv_int('rev')
        ts = self.req.psv_int('ts') or cur_ts
        name = self.req.psv_ustr('name')[:128].strip()
        recs = self.req.psv_js('recs')
        nums = [ int(x['num']) for x in recs if x.get('num') ]
        if len(nums) != len(set(nums)): self.req.exitjs({'err': 'Len Not Matched'})
        
        
        users = self.getuserlist()
        users_lku = dict([x[:2] for x in users])
        
        payments = self.getconfigv2('payments')
        payments_lku = payments and dict(json.loads(payments)) or {}
        
        
        cur = self.cur()
        
        orig_nums_lku = {}
        if d_id:
            cur.execute('select * from delivery where id=%s', (d_id,))
            rows = cur.fetchall()
            if not rows: self.req.exitjs({'err': 'No Record ID #%s' % (d_id,)})
            r = dict(zip(cur.column_names, rows[0]))
            if r['rev'] != rev: self.req.exitjs({'err': 'Revision Not Matched (%d, %d)' % (r['rev'], rev)})
            for n in json.loads(r['js']): orig_nums_lku[n] = [False]
        
        nums_lku = {}
        if nums:
            cur.execute('select r.num,r.sid,r.sid_type,rr.delivery_id from sync_receipts r left join receipt rr on (r.sid=rr.sid and r.sid_type=rr.sid_type) where r.num in (%s)' % (','.join(map(str,nums)),))
            for r in cur.fetchall():
                nums_lku[ r[0] ] = r
        
        err = []
        v_recs = []
        js_nums = []
        for i in range( len(recs) ):
            rec = recs[i]
            num = int(rec.get('num') or 0)
            if not num: continue
            
            chg = int(rec.get('changed') or 0)
            r = nums_lku.get(num)
            if chg or not orig_nums_lku.has_key(num):
                if r:
                    delivery_id = r[3] or 0
                    if delivery_id and delivery_id != d_id:
                        err.append('row#%d receipt#%d already assigned to record#%d' % (i + 1, num, delivery_id))
                        continue
                else:
                    err.append('row#%d receipt#%d not exists' % (i + 1, num))
                    continue
            
                rec['num'] = num
                rec['driver_id'] = int(rec['driver_id'])
                rec['delivered'] = int(bool(rec['delivered']))
                rec['payment_required'] = int(bool(rec['payment_required']))
                rec['problem'] = int(bool(rec['problem']))
                rec['memo'] = rec['problem'] and rec['memo'][:256].strip() or ''
                
                r_js = {}
                payment = rec['js'].get('payment', [0, 0, ''])
                payment = r_js['payment'] = [ int(payment[0]), float(payment[1]), payment[2][:256].strip() ]
                if not payment[0]:
                    payment[1] = 0
                    payment[2] = ''
                rec['js'] = r_js
            
                v_recs.append( (r[1], r[2], rec) )
            
            js_nums.append(num)
            orig_nums_lku.get(num, [False])[0] = True
            
        if err: self.req.exitjs({'err': '\n'.join(err)})
        
        if d_id:
            cur.execute('update delivery set rev=rev+1,count=%s,ts=%s,mts=%s,name=%s,js=%s where id=%s and rev=%s', (
                len(js_nums), ts, cur_ts, name, json.dumps(js_nums, separators=(',',':')), d_id, rev
                )
            )
            if cur.rowcount <= 0: self.req.exitjs({'err': 'Can Not Upate Record ID #%s' % (d_id,)})
        else:
            cur.execute('insert into delivery values (null,0,%s,%s,%s,%s,%s,%s)', (
                self.user_id, len(js_nums), ts, cur_ts, name, json.dumps(js_nums, separators=(',',':'))
                )
            )
            d_id = cur.lastrowid
            
        for sid,sid_type,rec in v_recs:
            f_delivered = (rec['delivered'] and REC_FLAG_DELIVERED or 0)
            f_problem = (rec['problem'] and REC_FLAG_PROBLEM or 0)
            f_pm_req = (rec['payment_required'] and REC_FLAG_PM_REQ or 0)
            
            s_js = json.dumps(rec['js'], separators=(',',':'))
            cur.execute('insert ignore into receipt values (%s,%s,%s,%s,%s,%s,%s,%s)', (
                sid, sid_type, f_delivered|f_problem|f_pm_req, rec['num'], d_id, rec['driver_id'], rec['memo'],
                s_js
                )
            )
            rc = cur.rowcount
            if rc <= 0:
                s_flag = (f_delivered and '(flag|%d)' or '(flag&~%d)') % (REC_FLAG_DELIVERED,)
                s_flag = (f_problem and '(%s|%d)' or '(%s&~%d)') % (s_flag, REC_FLAG_PROBLEM,)
                s_flag = (f_pm_req and '(%s|%d)' or '(%s&~%d)') % (s_flag, REC_FLAG_PM_REQ,)
                
                cur.execute('update receipt set delivery_id=%s,driver_id=%s,flag='+s_flag+',memo=%s,js=%s where sid=%s and sid_type=%s and (delivery_id=0 or delivery_id=%s)', (
                    d_id, rec['driver_id'], rec['memo'], s_js, sid, sid_type, d_id
                    )
                )
                rc = cur.rowcount
                
            if rc > 0:
                pm = rec['js']['payment']
                self.add_comment((sid, sid_type), 1, None, 'SetDelivery -> ID#%d Driver(%s) PRCV(%s) Delivered(%s) Problem(%s) PREQ(%s)' % (
                    d_id,
                    rec['driver_id'] and users_lku.get(rec['driver_id'], 'UNK') or '',
                    pm[0] and '%s,$%0.2f' % (payments_lku.get(pm[0], 'UNK'), pm[1]) or '',
                    f_delivered and 'Y' or 'N',
                    f_problem and 'Y' or 'N',
                    f_pm_req and 'Y' or 'N',
                    )
                )
        
        nums = [ x[0] for x in orig_nums_lku.items() if not x[1][0] ]
        if nums: 
            cur.execute('select sid,sid_type from sync_receipts where num in (%s)' % (','.join(map(str,nums)),))
            for r in cur.fetchall():
                cur.execute('update receipt set delivery_id=0 where sid=%s and sid_type=%s and delivery_id=%s', (
                    r[0], r[1], d_id
                    )
                )
                if cur.rowcount > 0:
                    self.add_comment(r, 1, None, 'SetDelivery -> remove from record #%d' % (
                        d_id
                        )
                    )
        
        self.req.writejs({'d_id': d_id})
        
    def fn_get_delivery_receipt(self):
        num = self.req.qsv_ustr('num')
        if not num: self.req.exitjs({'err': 'error Num'})
        
        cur = self.cur()
        cur.execute('select r.num,r.sid,r.sid_type,r.cid,r.global_js,rr.delivery_id,rr.driver_id,rr.flag,rr.memo,rr.js from sync_receipts r left join receipt rr on (r.sid=rr.sid and r.sid_type=rr.sid_type) where r.num=%s', (num,))
        rows = cur.fetchall()
        if not rows: self.req.exitjs({'err': 'No Such Receipt(%s)' % (num,)})
        r = dict(zip(cur.column_names, rows[0]))
        preset = bool(r['delivery_id'] != None)
        rec = self.make_rec(r)
        rec['preset'] = int(preset)
        self.req.writejs({'rec': rec})
    
    def fn_get_delivery_record_list(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select d.id,d.name,u.user_name,d.count,d.ts from delivery d left join user u on (d.user_id=u.user_id) order by d.id desc limit %d,%d' % (
                        sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                r = list(r)
                r[4] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(r[4]))
                apg.append(r)
        
        cur.execute('select count(*) from delivery')
        rlen = int(cur.fetchall()[0][0])
        
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
        