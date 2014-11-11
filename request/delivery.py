import json
import time
import config
import datetime
import bisect
import base64

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

REC_FLAG_PARTIAL = 1 << 6

DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        r = {}
        r['has_perm_admin'] = self.user_lvl & (1 << config.USER_PERM_BIT['admin'])
        self.req.writefile('delivery_v2.html', r)
    
    def fn_get_delivery_record(self):
        d_id = self.req.qsv_int('d_id')
        if not d_id: return
        self.req.writejs( self.get_delivery_record(d_id) )
    
    def get_delivery_record(self, d_id, mode=0):
        cur = self.cur()
        cur.execute('select * from deliveryv2 where d_id=%s', (d_id,))
        rows = cur.fetchall()
        if not rows: self.req.exitjs({'msg': 'No Record ID #%s' % (d_id,)})
        dv = dict(zip(cur.column_names, rows[0]))
        js = json.loads(dv['js'])
        
        rec_lku = {}
        cur.execute('select dr.*,sr.sid,sr.sid_type,sr.cid,sr.global_js,(select sonum from sync_salesorders where sid=sr.so_sid) as so_num,(select count(*) from deliveryv2_receipt sdr where sdr.num=dr.num) as dup,sc.sc_id,sc.sc_flag,sc.doc_type,sc.doc_sid,sc.sc_note from deliveryv2_receipt dr left join sync_receipts sr on (dr.num=sr.num) left join schedule sc on (dr.sc_id=sc.sc_id) where dr.d_id=%s', (d_id,))
        nzs = cur.column_names
        cids = set()
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            r['dup'] = r['dup'] > 1 and 1 or 0
            rec_lku[ r['num'] ] = r
            cids.add(r['cid'])

            if r['sc_id']:
                r['sc_mode'] = r['sc_flag'] & REC_FLAG_PARTIAL
                if r['doc_type']:
                    r['doc_num'] = r['num']
                else:
                    r['doc_num'] = r['so_num']
        
        for x in js:
            if x['type'] == 1:
                cids.add(x['cid'])
        
        cids.discard(None)
        cids_lku = {}
        if cids:
            cur.execute('select sid,name,detail from sync_customers where sid in (%s)' % (','.join(map(str,cids)),))
            for r in cur.fetchall():
                cust_gjs = r[2] and json.loads(r[2]) or {}
                cids_lku[ r[0] ] = {'company': r[1], 'terms': cust_gjs.get('udf5') or '', 'gjs': cust_gjs}
        
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
                if mode: r['gjs'] = r['global_js']
                
                cust = r['global_js'].get('customer') or {}
                r['company'] = cust.get('company') or cust.get('name') or ''
                r['amount'] = r['global_js'].get('total') or 0
                r['sid'] = r.get('sid') != None and str(r['sid']) or ''
                r['cid'] = cid != None and str(cid) or ''
                l['js'] = r.get('js') != None and json.loads(r['js']) or {}
                if cid and cids_lku.has_key(cid): r['terms'] = cids_lku[cid]['terms']
                r['global_js'] = None
                
            else:
                r = cids_lku.get(l['cid'])
                if not r:
                    msgs.append('customer#%d not exists' % (l['cid'], ))
                    r = {}
                l['payment_required'] = 1
                l['cid'] = str(l['cid'])
                if not mode: r['gjs'] = None
                
            r.update(l)
            recs.append(r)
        
        for num,r in rec_lku.items():
            if r.get('inc'): continue
            msgs.append('receipt#%d not included, out of sync' % (r['num'],))
        
        dv['js'] = ''
        dv['recs'] = recs
        dv['msg'] = '\n'.join(msgs)
        
        return dv
    
    def fn_get_delivery_record_list(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            d_users = dict([f_v[:2] for f_v in self.getuserlist()])
            cur.execute('select d_id,name,user_id,count,ts,(select group_concat(distinct driver_id) from deliveryv2_receipt where d_id=d.d_id) from deliveryv2 d order by d_id desc limit %d,%d' % (
                        sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                r = list(r)
                if r[5]:
                    drvs = ','.join([ d_users.get(int(f_v)) or f_v for f_v in r[5].split(',') if f_v.isdigit() ])
                else:
                    drvs = ''
                r[1] = u'%s - %s' % (r[1], drvs)
                r[2] = d_users.get(r[2])
                r[3] = '%d/%d' % ((r[3] >> 16) & 0xFF, r[3] & 0xFF)
                r[4] = time.strftime("%m/%d/%Y", time.localtime(r[4]))
                apg.append(r[:-1])
        
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


    def get_sc_recs(self, num, d_dt_i):
        cur = self.cur()
        cur.execute('select sid,so_sid,(select sonum from sync_salesorders where sid=sr.so_sid) as so_num from sync_receipts sr where sid_type=0 and num=%s', (num, ))
        rows = cur.fetchall()
        if not rows: return
        sid,so_sid,so_num = rows[0]

        sc_recs = []
        if so_sid != None:
            cur.execute('select sc_id,sc_flag,doc_type,doc_sid,sc_note from schedule where sc_date=%s and (doc_type=1 and doc_sid=%s or doc_type=0 and doc_sid=%s) order by doc_type desc', (d_dt_i, sid, so_sid))
        else:
            cur.execute('select sc_id,sc_flag,doc_type,doc_sid,sc_note from schedule where sc_date=%s and doc_type=1 and doc_sid=%s ', (d_dt_i, sid))
        cnz = cur.column_names
        for s in cur.fetchall():
            s = dict(zip(cnz, s))
            s['sc_mode'] = s['sc_flag'] & REC_FLAG_PARTIAL
            if s['doc_type']:
                s['doc_num'] = num
            else:
                s['doc_num'] = so_num
            sc_recs.append(s)

        return sc_recs


    def fn_get_sc_recs(self):
        num = self.req.qsv_int('num')
        if not num: return
        d_ts = self.req.qsv_int('d_ts')
        if d_ts:
            d_dt = datetime.date.fromtimestamp(d_ts)
        else:
            d_dt = datetime.date.today()
        d_dt_i = d_dt.year * 10000 + d_dt.month * 100 + d_dt.day

        self.req.writejs(self.get_sc_recs(num, d_dt_i)) 

    def fn_get_delivery_receipt(self):
        num = self.req.qsv_int('num')
        if not num: self.req.exitjs({'err': 'error Num'})
        d_id = self.req.qsv_int('d_id')
        d_ts = self.get_day_ts( self.req.qsv_int('d_ts') )
        d_dt = datetime.date.fromtimestamp(d_ts)
        d_dt_i = d_dt.year * 10000 + d_dt.month * 100 + d_dt.day
        
        cur = self.cur()
        cur.execute('select sr.num,sr.cid,sr.sid,sr.sid_type,sr.so_sid,sr.global_js,sc.detail from sync_receipts sr left join sync_customers sc on (sc.sid=sr.cid) where sr.sid_type=0 and sr.num=%s', (num, ))
        rows = cur.fetchall()
        if not rows: self.req.exitjs({'err': 'No Such Receipt(%s)' % (num,)})
        r = dict(zip(cur.column_names, rows[0]))
        
        sc_recs = r['sc_recs'] = self.get_sc_recs(num, d_dt_i)
        r['sc_count'] = len(sc_recs)
        if not r['sc_count']: self.req.exitjs({'err': 'No Schedule Found For Receipt(%s) in %02d/%02d' % (num, d_dt.month, d_dt.day)})
        
        cur.execute('select count(*),bit_and(dr.problem_flag_s<>0),bit_and(ifnull(s.sc_flag, 0)) from deliveryv2_receipt dr left join deliveryv2 d on (dr.d_id=d.d_id) left join schedule s on (dr.sc_id=s.sc_id) where dr.num=%s and dr.d_id!=%s and d.ts<=%s', (
            num, d_id, d_ts
            )
        )
        s_dup,s_pb_flag,s_sc_flag = cur.fetchall()[0]
        r['data'] = (s_dup,s_pb_flag,s_sc_flag)
        if s_dup and not(s_sc_flag & REC_FLAG_PARTIAL) and not s_pb_flag:
            self.req.exitjs({'err': "Receipt(%s) Duplicated, No Redelivery Is Allowed.\n*** Except all previous shipments are marked with problems!" % (num, )})
        r['dup'] = s_dup

        r['sid'] = str(r['sid'])
        r['cid'] = r['cid'] != None and str(r['cid']) or ''
        r['global_js'] = r['global_js'] and json.loads(r['global_js']) or {}
        cust = r['global_js'].get('customer') or {}
        r['company'] = cust.get('company') or cust.get('name') or ''
        r['amount'] = r['global_js']['total']
        r['global_js'] = ''
        
        r['detail'] = r['detail'] and json.loads(r['detail']) or {}
        r['terms'] = r['detail'].get('udf5') or ''
        r['detail'] = ''
        
        self.req.writejs({'rec': r})

    def add_comment(self, rid, c_type, user_name, comment):
        #cur = self.cur()
        #cur.execute('insert into receipt_comment values (null,%s,%s,%s,%s,%s,%s)', (
        #    rid[0], rid[1], int(time.time()), c_type, user_name or self.user_name, comment
        #    )
        #)
        self.cur().execute('insert into doc_note values(null,'+str(int(time.time()))+',%s,%s,0,'+str(self.user_id)+',%s)', (rid[1] and 2 or 1, rid[0], comment))

    def get_day_ts(self, ts):
        tp = time.localtime(ts or None)
        ts = int(time.mktime(datetime.date(tp.tm_year, tp.tm_mon, tp.tm_mday).timetuple()))
        return ts
    
    def fn_save_delivery_record(self):
        cur_ts = int(time.time())
        d_id = self.req.psv_int('d_id')
        rev = self.req.psv_int('rev')
        
        ts = self.get_day_ts( self.req.psv_int('ts') )
        d_dt = datetime.date.fromtimestamp(ts)
        d_dt_i = d_dt.year * 10000 + d_dt.month * 100 + d_dt.day
        
        name = self.req.psv_ustr('name')[:128].strip()
        recs = self.req.psv_js('recs')
        nums = [ int(x['num']) for x in recs if x.get('type') == 0 ]
        if len(nums) != len(set(nums)): self.req.exitjs({'err': 'duplicated receipt found'})
        
        users = self.getuserlist()
        users_lku = dict([x[:2] for x in users])
        
        cur = self.cur()
        
        date_chg = True
        orig_nums_lku = {}
        if d_id:
            cur.execute('select * from deliveryv2 where d_id=%s', (d_id,))
            rows = cur.fetchall()
            if not rows: self.req.exitjs({'err': 'No Record ID #%s' % (d_id,)})
            r = dict(zip(cur.column_names, rows[0]))
            if self.get_day_ts(r['ts']) == ts: date_chg = False
            if r['rev'] != rev: self.req.exitjs({'err': 'Revision Not Matched (%d, %d)' % (r['rev'], rev)})
            for n in json.loads(r['js']):
                if n['type'] == 0:
                    orig_nums_lku[ n['num'] ] = [False, n]
        
        nums_lku = {}
        if nums:
            qs_sc = '(select group_concat(sc_id) from schedule where sc_date='+str(d_dt_i)+' and (doc_type=1 and doc_sid=sr.sid or sr.so_sid is not null and doc_type=0 and doc_sid=sr.so_sid)) as sc_ids'
            cur.execute('select num,sid,sid_type,'+qs_sc+' from sync_receipts sr where num in ('+','.join(map(str,nums))+')')
            for r in cur.fetchall():
                r = list(r)
                if r[3]: r[3] = set(map(int, r[3].split(',')))
                nums_lku[ r[0] ] = r
        
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
            
            rec['sc_id'] = int(rec.get('sc_id') or 0)
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
                n_rec_js = orig_nums_lku.get(rec['num'])
                is_new = is_new_sc_id = False
                if not n_rec_js:
                    is_new = is_new_sc_id = True
                else:
                    is_new_sc_id = n_rec_js[1].get('sc_id', 0) != rec['sc_id']

                if date_chg or rec['changed'] or is_new or is_new_sc_id:
                    r = nums_lku.get(rec['num'])
                    if not r:
                        err.append('row#%d receipt#%d not exists' % (i + 1, rec['num']))
                        continue

                    if date_chg or is_new_sc_id:
                        if not r[3] or rec['sc_id'] not in r[3]:
                            err.append('row#%d receipt#%d - schedule(#%d) not in %02d/%02d' % (i + 1, rec['num'], rec['sc_id'], d_dt.month, d_dt.day))
                            continue

                        cur.execute('select count(*),bit_or((dr.sc_id=%s) & (dr.problem_flag_s=0)),bit_and(dr.problem_flag_s<>0),bit_and(ifnull(s.sc_flag, 0)),bit_or(ifnull(s.sc_flag, 1)) from deliveryv2_receipt dr left join deliveryv2 d on (dr.d_id=d.d_id) left join schedule s on (dr.sc_id=s.sc_id) where dr.num=%s and dr.d_id!=%s and d.ts<=%s', (
                                rec['sc_id'], rec['num'], d_id, ts
                            )
                        )
                        s_dup,s_sp_pb,s_pb_flag,s_sc_flag,s_sc_flag_v2 = cur.fetchall()[0]
                        if s_dup:
                            if not(s_sc_flag & REC_FLAG_PARTIAL) and not s_pb_flag:
                                err.append('row#%d receipt#%d - need to mark all previous shipments with problems' % (i + 1, rec['num']))
                                continue

                            if s_sp_pb:
                                err.append('row#%d receipt#%d - need to mark all previous shipments(using schedule#%d) with problems' % (i + 1, rec['num'], rec['sc_id']))
                                continue

                            if s_sc_flag_v2 & REC_FLAG_PARTIAL:
                                cur.execute('select sc_flag from schedule where sc_id=%s', (rec['sc_id'], ))
                                if not(cur.fetchall()[0][0] & REC_FLAG_PARTIAL):
                                    err.append('row#%d receipt#%d - Completed Delivery Is Not Allowed' % (i + 1, rec['num']))
                                    continue

                    
                    recs_db.append( (rec, r, is_new) )
                
                recs_js.append( {'type': 0, 'num': rec['num'], 'sc_id': rec['sc_id']} )
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
        
        rec_exists = {}
        if recs_db:
            cur.execute('select num,count(*) from deliveryv2_receipt where d_id!=%d and num in (%s) group by num' % (
                d_id, ','.join([ str(f_rec['num']) for f_rec,f_r,f_is_new in recs_db ])
                )
            )
            for r in cur.fetchall(): rec_exists[ r[0] ] = r[1]
        
        for rec,r,is_new in recs_db:
            s_js = json.dumps(rec['js'], separators=(',',':'))
            cur.execute('insert into deliveryv2_receipt values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) on duplicate key update sc_id=%s,driver_id=%s,delivered=%s,user_id=%s,payment_required=%s,problem_flag=%s,problem_flag_s=problem_flag_s|%s,js=%s', (
                d_id, rec['num'], int(bool(rec_exists.get(rec['num'], 0))), rec['sc_id'], rec['driver_id'], rec['delivered'], 0, rec['payment_required'], rec['problem_flag'], rec['problem_flag'], s_js,
                rec['sc_id'], rec['driver_id'], rec['delivered'], 0, rec['payment_required'], rec['problem_flag'], rec['problem_flag'], s_js
                )
            )
            rc = cur.rowcount
            if rc > 0:
                nl = ['%s DeliveryLog(#%d), Schedule(%d), Driver - %s' % (
                    is_new and 'Add To' or 'Update',
                    d_id, rec['sc_id'],
                    rec['driver_id'] and users_lku.get(rec['driver_id'], 'UNK') or '',
                )]
                if rec['payment_required']: nl.append('> Payment Required')
                if rec['js']['payments']: nl.append('> Payment Received: $%0.2f' % ( sum([f_x[1] for f_x in rec['js']['payments']]), ))
                if rec['delivered']: nl.append('> Delivered')
                if rec['problem_flag']:
                    #nl.append('> Problem Occurred')
                    nl.extend([ '> Problem - ' + PROBLEMS[int(f_i)] + (f_v[1] and ': ' + f_v[1] or '') for f_i,f_v in rec['js']['problems'].items() ])
                
                self.add_comment((r[1], r[2]), 1, None, '\n'.join(nl))
        
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
                cust = r['global_js'].get('customer') or {}
                r['company'] = cust.get('company') or cust.get('name') or ''
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
        
            cur.execute('select SQL_CALC_FOUND_ROWS r.num,sr.global_js,d.user_id,r.d_id,r.driver_id,d.name,sr.order_date,d.ts,r.js,sr.sid,sr.sid_type,sr.cid from deliveryv2_receipt r left join sync_receipts sr on (sr.num=r.num) left join deliveryv2 d on (r.d_id=d.d_id) where d.d_id is not null and sr.num is not null and r.problem_flag!=0 order by r.num desc, r.d_id desc limit %d,%d' % (
                sidx * pgsz, (eidx - sidx) * pgsz
                )
            )
            
            for r in cur.fetchall():
                r = list(r)
                
                r[1] = r[1] and json.loads(r[1]) or {}
                cust = r[1].get('customer') or {}
                r[1] = cust.get('company') or cust.get('name') or ''
                r[2] = r[2] and users_lku.get(r[2], 'UNK') or ''
                r[4] = r[4] and users_lku.get(r[4], 'UNK') or ''
                r[6] = time.strftime("%m/%d/%y", time.localtime(r[6]))
                r[7] = time.strftime("%m/%d/%y", time.localtime(r[7]))
                r[8] = ', '.join([ PROBLEMS[int(f_i)] + (f_v[1] and ': ' + f_v[1] or '') for f_i,f_v in ((r[8] and json.loads(r[8]) or {}).get('problems') or {}).items() ])
                r[9] = str(r[9])
                r[11] = str(r[11])
                
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
        r = {
            'mons_total': self.get_report__mons_total(),
            'delivery_completed': self.get_report__delivery_completed()
        }
        self.req.writefile('delivery_v2_report.html', r)
    fn_report.PERM = 1 << config.USER_PERM_BIT['admin']
    
    def get_report__mons_total(self):
        js = self.get_data_file_cached('delivery_report', 'delivery_report.txt')
        if not js: return
        
        rjs = self.get_data_file_cached('receipt_report', 'receipt_report.txt')
        rd = rjs and rjs['summary'] or []
        
        lst = []
        for m,d in js['mons'][-8:]:
            r = None
            idx = bisect.bisect_left([f_x[0] for f_x in rd], m)
            if idx < len(rd) and rd[idx][0] == m: r = rd[idx][1]
            
            lst.append({
                'date': time.strftime("%y-%m", time.localtime(m)),
                'total': len(d['nums']),
                'line': d['lines'],
                'qty': d['qtys'],
                
                'receipt_count': r and r[8] or 0,
                'receipt_sale': r and r[4] or 0,
            })
        
        lst.reverse()
        return lst
    
    def get_report__delivery_completed(self):
        frm_ts = int(time.mktime((datetime.date.today() - datetime.timedelta(8)).timetuple()))
        
        md = {}
        cur = self.cur()
        cur.execute('select ts,count from deliveryv2 where ts>=%s', (
            frm_ts,
            )
        )
        for r in cur.fetchall():
            ts,count = r
            tp = time.localtime(ts)
            dt = int(time.mktime(datetime.date(tp.tm_year, tp.tm_mon, tp.tm_mday).timetuple()))
            d = md.setdefault(dt, [0, 0])
            d[0] += count & 0xFF
            d[1] += (count >> 16) & 0xFF
            
        md = md.items()
        md.sort(key=lambda f_x:f_x[0])
        md = [ {'date': time.strftime("%m/%d", time.localtime(f_t)), 'total': f_d[0], 'comp': f_d[1]} for f_t,f_d in md ]
        md.reverse()
        
        return md


    def fn_get_drec(self):
        d_id = self.req.qsv_int('d_id')
        if not d_id: return
        
        cur = self.cur()
        locs = set()
        
        dr = self.get_delivery_record(d_id, 1)
        for r in dr['recs']:
            loc = None
            if r['type']:
                if r['gjs']:
                    loc = r['gjs'].get('loc')
            else:
                if r['gjs']:
                    if r['gjs']['shipping']:
                        loc = r['gjs']['shipping'].get('loc')
                    elif r['gjs']['customer']:
                        loc = r['gjs']['customer'].get('loc')
        
            if loc != None:
                loc = base64.b64decode(loc)
                locs.add(loc)
            
            r['loc'] = loc
            r['gjs'] = None
        
        d_loc = {}
        if locs:
            cur.execute('select loc,zone_id,lat,lng from address where loc in ('+','.join(['%s'] * len(locs))+') and flag=1', tuple(locs))
            for r in cur.fetchall(): d_loc[ r[0] ] = (r[1], str(r[2]), str(r[3]))
        
            for r in dr['recs']:
                geo = d_loc.get(r['loc'])
                if geo: r['geo'] = ( geo[0], str(geo[1]), str(geo[2]) )
                r['loc'] = None
        
        dr['lst'] = dr['recs']
        dr['recs'] = None
        self.req.writejs(dr)

    def fn_map(self):
        d_id = self.qsv_int('d_id')
        r = {
            'd_id': d_id,
        }
        
        self.req.writefile('map_delivery.html', r)

