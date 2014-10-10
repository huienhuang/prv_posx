import json
import time
import config
import datetime
import base64
import const

ZONES = const.ZONES
MAX_DAYS = 7
WDAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

SALES_PERM = 1 << config.USER_PERM_BIT['sales']
DELIVERY_MGR_PERM = 1 << config.USER_PERM_BIT['delivery_mgr']
PURCHASING_PERM = 1 << config.USER_PERM_BIT['purchasing']


REC_FLAG_ACCEPTED = 1 << 0
REC_FLAG_RESCHEDULED = 1 << 1
REC_FLAG_CANCELLING = 1 << 2
REC_FLAG_CHANGED = 1 << 3
REC_FLAG_DUPLICATED = 1 << 4
REC_FLAG_R_RESCHEDULED = 1 << 5
REC_FLAG_PARTIAL = 1 << 6
REC_FLAG_PARTIAL_CHANGED = 1 << 7

CFG_SCHEDULE_UPDATE_SEQ = config.CFG_SCHEDULE_UPDATE_SEQ


ORD_TYPE=('Sales', 'Return', 'Deposit', 'Refund', 'Payout', 'Payin')


DEFAULT_PERM = SALES_PERM | DELIVERY_MGR_PERM | PURCHASING_PERM
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        r = {
            'sales': [ f_user for f_user in self.getuserlist() if f_user[2] & SALES_PERM ],
            'zones': [ (f_x[0], f_x[2]) for f_x in ZONES ],
            'has_perm_delivery_mgr': self.user_lvl & DELIVERY_MGR_PERM,
            'REC_FLAG_CANCELLING': REC_FLAG_CANCELLING,
            'REC_FLAG_ACCEPTED': REC_FLAG_ACCEPTED,
            'REC_FLAG_RESCHEDULED': REC_FLAG_RESCHEDULED,
            'REC_FLAG_CHANGED': REC_FLAG_CHANGED,
            'REC_FLAG_DUPLICATED': REC_FLAG_DUPLICATED,
            'REC_FLAG_R_RESCHEDULED': REC_FLAG_R_RESCHEDULED,
            'REC_FLAG_PARTIAL': REC_FLAG_PARTIAL,
            'REC_FLAG_PARTIAL_CHANGED': REC_FLAG_PARTIAL_CHANGED,
            'CFG_SCHEDULE_UPDATE_SEQ': CFG_SCHEDULE_UPDATE_SEQ,
            'sc_upd_seq': self.getconfig(CFG_SCHEDULE_UPDATE_SEQ)
        }
        self.req.writefile('schedule_v2.html', r)
    
    def inc_seq(self):
        self.cur().execute('update config set cval=cval+1 where cid=%s', (CFG_SCHEDULE_UPDATE_SEQ,))
    
    def add_notes(self, lst):
        self.cur().executemany('insert into doc_note values(null,'+str(int(time.time()))+',%s,%s,0,'+str(self.user_id)+',%s)', lst)
    
    def fn_del_rec(self):
        d_date = datetime.date.today()
        d_date = d_date.year * 10000 + d_date.month * 100 + d_date.day
        sc_id = self.req.psv_int('sc_id')
        
        cur = self.cur()

        cur.execute('select count(*) from deliveryv2_receipt where sc_id=%s', (sc_id, ))
        if cur.fetchall()[0][0]: self.req.exitjs({'err': -12, 'err_s': "It's In Use! Aborted"})

        cur.execute('select * from schedule where sc_id=%s and sc_date>=%s', (sc_id, d_date))
        rows = cur.fetchall()
        if not rows: return
        r = dict(zip(cur.column_names, rows[0]))
        
        if r['sc_flag'] & REC_FLAG_CANCELLING:
            self.req.exitjs({'err': -11, 'err_s': 'Cancellation is already pending'})
        
        m,d = divmod(r['sc_date'], 100)
        y,m = divmod(m, 100)
        
        d_note = None
        if r['sc_flag'] & REC_FLAG_ACCEPTED:
            cur.execute('update schedule set sc_rev=sc_rev+1,sc_flag=sc_flag|%s where sc_id=%s and sc_rev=%s and sc_flag&%s!=0 and (select count(*) from deliveryv2_receipt where sc_id=schedule.sc_id)=0', (
                REC_FLAG_CANCELLING, sc_id, r['sc_rev'], REC_FLAG_ACCEPTED
                )
            )
            d_note = 'Schedule[%d] (%02d/%02d/%02d) - Deleting, Waiting For Confirmation' % (r['sc_id'], m, d, y)
        else:
            cur.execute('delete from schedule where sc_id=%s and sc_rev=%s and sc_flag&%s=0 and (select count(*) from deliveryv2_receipt where sc_id=schedule.sc_id)=0', (
                sc_id, r['sc_rev'], REC_FLAG_ACCEPTED
                )
            )
            d_note = 'Schedule[%d] (%02d/%02d/%02d) - Deleted' % (r['sc_id'], m, d, y)
            
        err = int(cur.rowcount <= 0)
        if not err:
            if d_note: self.add_notes(([r['doc_type'], r['doc_sid'], d_note],))
            self.inc_seq()
        
        self.req.writejs({'err': err})
    
    def fn_del(self):
        sc_ids = map(int, self.req.psv_ustr('sc_ids').split('|'))
        docs = self.get_docs_by_sc_ids(sc_ids)
        #if len(sc_ids) != len(docs): self.req.exitjs({'err': -2, 'err_s': "size not matched"})
        
        d_notes = []
        cur = self.cur()
        c = 0
        for r in docs:
            cur.execute('delete from schedule where sc_id=%s and sc_flag&%s!=0 and (select count(*) from deliveryv2_receipt where sc_id=schedule.sc_id)=0', (
                r['sc_id'], REC_FLAG_CANCELLING
            ))
            if cur.rowcount > 0:
                c += 1
                m,d = divmod(r['sc_date'], 100)
                y,m = divmod(m, 100)
                d_notes.append([r['doc_type'],
                                r['doc_sid'],
                                'Schedule[%d] (%02d/%02d/%02d) - Confirmed > Deleted' % (r['sc_id'], m, d, y)
                ])
    
        if c:
            if d_notes: self.add_notes(d_notes)
            self.inc_seq()
            
        i_warning_s = None
        if len(sc_ids) != c: i_warning_s = '%d out of %d processed' % (c, len(sc_ids))
        
        self.req.writejs({'err': 0, 'i_warning_s': i_warning_s})
    fn_del.PERM = DELIVERY_MGR_PERM
    
    def fn_confirm_rescheduling(self):
        sc_ids = map(int, self.req.psv_ustr('sc_ids').split('|'))
        docs = self.get_docs_by_sc_ids(sc_ids, True)
        
        d_notes = []
        cur = self.cur()
        c = 0
        for r in docs:
            if not(r['sc_flag'] & REC_FLAG_PARTIAL):
                cur.execute('select bit_or(sc_flag) from schedule where sc_date<=%s and sc_id!=%s and doc_type=%s and doc_sid=%s', (
                    r['sc_new_date'], r['sc_id'], r['doc_type'], r['doc_sid']
                    )
                )
                if cur.fetchall()[0][0] & REC_FLAG_PARTIAL: continue
            else:
                cur.execute('select bit_and(sc_flag) from schedule where sc_date>=%s and sc_id!=%s and doc_type=%s and doc_sid=%s', (
                    r['sc_new_date'], r['sc_id'], r['doc_type'], r['doc_sid']
                    )
                )
                if not(cur.fetchall()[0][0] & REC_FLAG_PARTIAL): continue

            cur.execute('update schedule set sc_rev=sc_rev+1,sc_flag=(sc_flag&(~%s))|%s,sc_date=%s,sc_new_date=0 where sc_id=%s and sc_rev=%s and sc_flag&%s=%s', (
                REC_FLAG_RESCHEDULED, REC_FLAG_R_RESCHEDULED, 
                r['sc_new_date'],
                r['sc_id'], r['sc_rev'],
                REC_FLAG_RESCHEDULED | REC_FLAG_CANCELLING, REC_FLAG_RESCHEDULED
                )
            )
            if cur.rowcount > 0:
                c += 1
                m,d = divmod(r['sc_date'], 100)
                y,m = divmod(m, 100)
                s_od = '%02d/%02d/%02d' % (m, d, y)
                m,d = divmod(r['sc_new_date'], 100)
                y,m = divmod(m, 100)
                s_nd = '%02d/%02d/%02d' % (m, d, y)
                
                d_notes.append([r['doc_type'],
                                r['doc_sid'],
                                'Reschedule[%d] From %s To %s - Confirmed' % (r['sc_id'], s_od, s_nd)
                ])
        if c:
            if d_notes: self.add_notes(d_notes)
            self.inc_seq()
            
        i_warning_s = None
        if len(sc_ids) != c: i_warning_s = '%d out of %d processed' % (c, len(sc_ids))
        
        self.req.writejs({'err': 0, 'i_warning_s': i_warning_s})
    fn_confirm_rescheduling.PERM = DELIVERY_MGR_PERM
    
    def fn_get_doc(self):
        d_num = self.req.qsv_ustr('num')
        if not d_num.isdigit(): return
        d_type = int(bool(self.req.qsv_int('type')))
        
        cur = self.cur()
        if d_type:
            cur.execute('select sid,num,assoc,order_date,global_js,items_js from sync_receipts where num=%s and sid_type=0 and (type&0xFF)=0 order by sid desc limit 1', (
                int(d_num),
                )
            )
        else:
            cur.execute('select sid,sonum,clerk,sodate,global_js,items_js from sync_salesorders where sonum=%s and (status>>4)=0 order by sid desc limit 1', (
                d_num,
                )
            )
        
        row = cur.fetchall()
        if not row: self.req.exitjs({'err': -1, 'err_s': 'document #%s not found' % (d_num,)})
        sid,num,assoc,doc_date,gjs,ijs = row[0]
        
        gjs = json.loads(gjs)
        cust = gjs.get('customer') or {}
        company = cust.get('company') or cust.get('name') or ''
        
        loc = None
        if gjs['shipping']:
            loc = gjs['shipping'].get('loc')
        elif gjs['customer']:
            loc = gjs['customer'].get('loc')
        
        zidx = 0
        if loc != None:
            cur.execute('select zone_id from address where loc=%s and flag=1', (base64.b64decode(loc),))
            rr = cur.fetchall()
            if rr: zidx = rr[0][0]
        
        n_ijs = []
        ijs = json.loads(ijs)
        for item in ijs:
            n_item = {
                'sid': str(item['itemsid']),
                'num': item['itemno'],
                'name': item['desc1'],
                'price': item['price'],
                'uom': item['uom'],
                'qty': item['qty'],
                'alu': item['alu'],
            }
            n_ijs.append(n_item)
        
        recs = []
        crc = gjs.get('crc')
        items_crc = gjs.get('items_crc')
        js = {
            'type': d_type,
            'num': num,
            'sid':str(sid),
            'assoc': assoc,
            'company': company,
            'total': gjs['total'],
            'recs': recs,
            'doc_date': time.strftime("%m/%d/%Y", time.localtime(doc_date)),
            'zone_nz': ZONES[zidx][0],
            'ijs' : n_ijs,
            'crc': crc,
            'items_crc': items_crc
        }
        
        cur.execute('select sc_id,sc_date,sc_new_date,sc_rev,sc_flag,sc_prio,doc_type,doc_sid,doc_crc,sc_note,doc_ijs_crc,doc_ijs from schedule where doc_type=%s and doc_sid=%s order by sc_id asc', (
            d_type, sid
            )
        )
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            
            if r['sc_flag'] & REC_FLAG_PARTIAL and r['doc_ijs_crc'] != items_crc: r['sc_flag'] |= REC_FLAG_PARTIAL_CHANGED
            if r['sc_flag'] & REC_FLAG_ACCEPTED and r['doc_crc'] != crc: r['sc_flag'] |= REC_FLAG_CHANGED

            if r['sc_flag'] & REC_FLAG_PARTIAL:
                doc_ijs = r['doc_ijs'] and json.loads(r['doc_ijs']) or []
                if r['sc_flag'] & REC_FLAG_PARTIAL_CHANGED:
                    r['doc_ijs'],r['unmatched'] = self.map_item(ijs, doc_ijs)
                else:
                    r['doc_ijs'] = [ {'qty': f_i['r_qty']} for f_i in doc_ijs ]
                    
            recs.append(r)
        
        self.req.writejs(js)
    
    def map_item(self, ijs, doc_ijs):
        d_items = {}
        for r in doc_ijs:
            if not r['r_qty']: continue
            v = d_items.setdefault((r['itemsid'], r['uom']), [0, {}])[1].setdefault(r['qty'], []).append(r['r_qty'])
            
        n_ijs = []
        for r in ijs:
            v = d_items.get((r['itemsid'], r['uom']))
            t = {'qty': 0, 'err': -1}
            n_ijs.append(t)
            if not v: continue
            
            v1 = v[1].get(r['qty'])
            if v1:
                t['qty'] = v1.pop(0)
                t['err'] = 0
            else:
                t['err'] = 1
                t['v'] = v
        
        unmatched = 0
        for r in n_ijs:
            if r['err'] != 1: continue
            v = r['v']
            if not v[0]:
                m = []
                for q,c_q_l in v[1].items():
                    for c_q in c_q_l:
                       m.append( (q, c_q) )
                v[0] = 1
                v[1] = m
            
            if len(v[1]):
                unmatched += 1
                r['qty'] = v[1].pop(0)[1]
            else:
                r['err'] = -1
        
        return (n_ijs, unmatched)
    
    def diff_items(self, c_ijs, o_ijs):
        d_t = {}

        for i in range(len(c_ijs)):
            t = c_ijs[i]
            d_t.setdefault((t['itemsid'], t['uom']), [0, i, t])[0] += t['qty']

        for i in range(len(o_ijs)):
            t = o_ijs[i]
            ct = d_t.setdefault((t['itemsid'], t['uom']), [0, i, t])
            ct[0] -= t['qty']

        ts = []
        for v in d_t.values():
            if not v[0]: continue
            ts.append(v)
        ts.sort(key=lambda f_v:(f_v[1], f_v[2]['itemno']))

        return ts

    def fn_set_doc(self):
        cts = int(time.time())
        d_sid = self.req.psv_int('sid')
        
        d_date = map(int, self.req.psv_ustr('date').split('/'))
        o_date = datetime.date(d_date[2], d_date[0], d_date[1])
        
        if o_date < datetime.date.today():
            if self.user_lvl & DELIVERY_MGR_PERM:
                pass
            else:
                self.req.exitjs({'err': -9, 'err_s': "Invalid Date"})
        d_date = o_date.year * 10000 + o_date.month * 100 + o_date.day
        
        d_type = int(bool(self.req.psv_int('type')))
        rev = self.req.psv_int('rev')
        prio = min(max(-1, self.req.psv_int('prio')), 2)
        sc_id = self.req.psv_int('sc_id')
        note = self.req.psv_ustr('note')[:256].strip()
        mode = self.req.psv_int('mode')

        d_notes = []
        cur = self.cur()
        if d_type:
            cur.execute('select num,global_js,items_js from sync_receipts where sid=%s and sid_type=0 and (type&0xFF)=0', (
                d_sid,
                )
            )
        else:
            cur.execute('select sonum,global_js,items_js from sync_salesorders where sid=%s and (status>>4)=0', (
                d_sid,
                )
            )
        
        row = cur.fetchall()
        if not row: return
        d_num,gjs,ijs = row[0]
        
        gjs = json.loads(gjs)
        new_doc_crc = gjs.get('crc')
        new_doc_ijs_crc = gjs.get('items_crc')
        
        if mode:
            if not note: self.req.exitjs({'err': -66, 'err_s': 'Require A Note For Partial Delivery!'})
            
            r_crc,r_ijs = self.req.psv_js('doc')
            
            ijs = json.loads(ijs)
            if new_doc_crc != r_crc: self.req.exitjs({'err': -11, 'err_s': 'Doc Changed, CRC Error!'})
            
            ijs_note = []
            for i in range(len(ijs)):
                r_item = r_ijs[i]
                item = ijs[i]
                r_qty = int(r_item[1])
                if int(r_item[0]) != item['itemsid'] or r_qty * item['qty'] < 0 or abs(r_qty) > abs(item['qty']):
                    self.req.exitjs({'err': -10, 'err_s': 'Item Unmatched!'})
                item['r_qty'] = r_qty
                if r_qty: ijs_note.append(u'> %d - %s - %s - %d / %d %s' % (item['itemno'], item['alu'], item['desc1'], r_qty, item['qty'], item['uom']))
            
            s_ijs = json.dumps(ijs, separators=(',',':'))

        if sc_id == 0:
            if not mode:
                cur.execute('select bit_or(sc_flag) from schedule where sc_date<=%s and doc_type=%s and doc_sid=%s', (
                    d_date, d_type, d_sid
                    )
                )
                if cur.fetchall()[0][0] & REC_FLAG_PARTIAL: self.req.exitjs({'err': -67, 'err_s': 'Completed Delivery Is Not Allowed!'})
            else:
                cur.execute('select bit_and(sc_flag) from schedule where sc_date>=%s and doc_type=%s and doc_sid=%s', (
                    d_date, d_type, d_sid
                    )
                )
                if not(cur.fetchall()[0][0] & REC_FLAG_PARTIAL): self.req.exitjs({'err': -67, 'err_s': 'Partial Delivery Is Not Allowed!'})

            cur.execute('insert into schedule values(null,%s,0,1,%s,%s,%s,%s,%s,%s,%s,%s,null)', (
                d_date, mode and REC_FLAG_PARTIAL or 0, prio, d_type, d_sid, new_doc_crc, note, new_doc_ijs_crc, mode and s_ijs or None
                )
            )
            sc_id = cur.lastrowid
            d_notes.append('Schedule[%d] (%s) - Created(Pending) - %s' % (sc_id, o_date.strftime('%m/%d/%y'), mode and 'Partial Delivery\n' + '\n'.join(ijs_note) or 'Complete Delivery'))
        else:
            cur.execute("select sc_flag,sc_date,sc_new_date,sc_prio,sc_note,doc_crc,doc_ijs,doc_ijs_crc from schedule where sc_id=%s and sc_rev=%s", (
                sc_id, rev
                )
            )
            row = cur.fetchall()
            if not row: self.req.exitjs({'err': -3, 'err_s': "document #%s - record #%s - can't find the record" % (d_num, sc_id)})
            o_r = dict(zip(cur.column_names, row[0]))
            new_sc_flag = o_r['sc_flag']
            
            chg = chk = False
            if o_r['sc_flag'] & REC_FLAG_CANCELLING: self.req.exitjs({'err': -2, 'err_s': "Cancellation is pending"})
            if o_r['sc_date'] != d_date and o_r['sc_new_date'] != d_date or o_r['sc_prio'] != prio or o_r['sc_note'] != note: chg = True
            if bool(o_r['sc_flag'] & REC_FLAG_PARTIAL) != bool(mode):
                chg = chk = True
                d_notes.append('Schedule[%d] (%s) - Changed Mode From %s To %s%s' % (
                    sc_id, o_date.strftime('%m/%d/%y'),
                    mode and 'Complete' or 'Partial',
                    mode and 'Partial' or 'Complete',
                    mode and '\n' + '\n'.join(ijs_note) or ''
                    )
                )
                if o_r['sc_flag'] & REC_FLAG_ACCEPTED: new_sc_flag |= REC_FLAG_CHANGED

            if mode and o_r['sc_flag'] & REC_FLAG_PARTIAL:
                m_note = False
                if new_doc_ijs_crc != o_r['doc_ijs_crc']:
                    m_note = chg = True
                    if not self.req.psv_int('check_n_confirm'): self.req.exitjs({'err': -12, 'err_s': "Items Changed! Please Check!"})
                    
                o_r['doc_ijs'] = o_r['doc_ijs'] and json.loads(o_r['doc_ijs']) or []
                

                a_l_ijs = [ (f_v['itemsid'], f_v['uom'], f_v['qty'], f_v['r_qty']) for f_v in ijs ]
                b_l_ijs = [ (f_v['itemsid'], f_v['uom'], f_v['qty'], f_v['r_qty']) for f_v in o_r['doc_ijs'] ]
                if a_l_ijs != b_l_ijs:
                    chg = True
                    if [ f_x for f_x in a_l_ijs if f_x[3] ] != [ f_x for f_x in b_l_ijs if f_x[3] ]:
                        m_note = False
                        d_notes.append('Schedule[%d] (%s) - Partial Delivery - Updated Packing List\n%s' % (
                            sc_id, o_date.strftime('%m/%d/%y'),
                            '\n'.join(ijs_note)
                            )
                        )
                        if o_r['sc_flag'] & REC_FLAG_ACCEPTED: new_sc_flag |= REC_FLAG_CHANGED
                    else:
                        m_note = True
                
                if m_note:
                    d_notes.append('Schedule[%d] (%s) - Partial Delivery - Checked' % (
                        sc_id, o_date.strftime('%m/%d/%y'),
                        )
                    )
                
            if not chg: self.req.exitjs({'err': -2, 'err_s': "document #%s - record #%s - nothing changed" % (d_num, sc_id)})
            
            if mode:
                new_sc_flag |= REC_FLAG_PARTIAL
            else:
                new_sc_flag &= (~REC_FLAG_PARTIAL)
            
            new_d_date = o_r['sc_new_date']
            if o_r['sc_date'] != d_date and o_r['sc_new_date'] != d_date:
                m,d = divmod(o_r['sc_date'], 100)
                y,m = divmod(m, 100)
                o_old_date = datetime.date(y, m, d)
                
                if o_r['sc_flag'] & REC_FLAG_ACCEPTED:
                    new_sc_flag |= REC_FLAG_RESCHEDULED
                    d_notes.append('Rescheduling[%d] From %s To %s, Waiting For Confirmation' % (sc_id, o_old_date.strftime('%m/%d/%y'), o_date.strftime('%m/%d/%y'), ))
                else:
                    d_notes.append('Reschedule[%d] From %s To %s' % (sc_id, o_old_date.strftime('%m/%d/%y'), o_date.strftime('%m/%d/%y'), ))
            
                chk = True
                new_d_date = d_date

            if chk:
                if not mode:
                    cur.execute('select bit_or(sc_flag) from schedule where sc_date<=%s and sc_id!=%s and doc_type=%s and doc_sid=%s', (
                        d_date, sc_id, d_type, d_sid
                        )
                    )
                    if cur.fetchall()[0][0] & REC_FLAG_PARTIAL: self.req.exitjs({'err': -67, 'err_s': 'Completed Delivery Is Not Allowed!'})
                else:
                    cur.execute('select bit_and(sc_flag) from schedule where sc_date>=%s and sc_id!=%s and doc_type=%s and doc_sid=%s', (
                        d_date, sc_id, d_type, d_sid
                        )
                    )
                    if not(cur.fetchall()[0][0] & REC_FLAG_PARTIAL): self.req.exitjs({'err': -67, 'err_s': 'Partial Delivery Is Not Allowed!'})

            if o_r['sc_flag'] & REC_FLAG_ACCEPTED:
                if o_r['sc_prio'] != prio or o_r['sc_note'] != note: new_sc_flag |= REC_FLAG_CHANGED
                if mode:
                    cur.execute("update schedule set sc_rev=sc_rev+1,sc_flag=%s,sc_new_date=%s,sc_prio=%s,sc_note=%s,doc_ijs_crc=%s,doc_ijs=%s where sc_id=%s and sc_rev=%s", (
                        new_sc_flag, new_d_date, prio, note, new_doc_ijs_crc, s_ijs, sc_id, rev
                        )
                    )
                else:
                    cur.execute("update schedule set sc_rev=sc_rev+1,sc_flag=%s,sc_new_date=%s,sc_prio=%s,sc_note=%s,doc_ijs=null where sc_id=%s and sc_rev=%s", (
                        new_sc_flag, new_d_date, prio, note, sc_id, rev
                        )
                    )
            else:
                cur.execute("update schedule set sc_rev=sc_rev+1,sc_new_date=0,sc_flag=%s,sc_date=%s,sc_prio=%s,sc_note=%s,doc_crc=%s,doc_ijs_crc=%s,doc_ijs=%s where sc_id=%s and sc_rev=%s", (
                    new_sc_flag,d_date, prio, note, new_doc_crc, new_doc_ijs_crc, mode and s_ijs or None, sc_id, rev
                    )
                )
            
        err = int(cur.rowcount <= 0)
        if err:
            self.req.exitjs({'err': -2, 'err_s': "document #%s - can't make any update" % (d_num, )})
        else:
            if d_notes: self.add_notes([ (d_type, d_sid, f_note) for f_note in d_notes ])
            self.inc_seq()
        
        self.req.exitjs({'err': err, 'sc_id': sc_id})
    
    def get_docs_by_sc_ids(self, sc_ids, full=False):
        if not sc_ids: return []
        sc_ids = sc_ids[:100]
        return self._get_docs_by_sc_ids(sc_ids, full)
        
    def _get_docs_by_sc_ids(self, sc_ids, full=False):
        so_sids = set()
        rc_sids = set()
        sc_lst = []
        
        cur = self.cur()
        cur.execute('select ' + (full and '*' or 'sc_id,sc_flag,sc_date,doc_type,doc_sid') + ' from schedule where sc_id in (%s)' % (','.join(map(str,sc_ids)),))
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            sc_lst.append(r)
            if r['doc_type']:
                rc_sids.add(r['doc_sid'])
            else:
                so_sids.add(r['doc_sid'])
                
        d_so = {}
        if so_sids:
            cur.execute('select ' + (full and 'sid,cust_sid,status,sonum,clerk,cashier,sodate,global_js,items_js' or 'sid,sonum,global_js') + ' from sync_salesorders where sid in (%s)' % (','.join(map(str, so_sids)), ))
            for r in cur.fetchall(): d_so[r[0]] = r
            
        d_rc = {}
        if rc_sids:
            cur.execute('select ' + (full and 'sid,cid,type,num,assoc,cashier,order_date,global_js,items_js' or 'sid,num,global_js') + ' from sync_receipts where sid_type=0 and sid in (%s)' % (','.join(map(str, rc_sids)), ))
            for r in cur.fetchall(): d_rc[r[0]] = r
        
        _sc_lst = []
        for r in sc_lst:
            if r['doc_type']:
                doc = d_rc.get(r['doc_sid'])
            else:
                doc = d_so.get(r['doc_sid'])
            if not doc: continue
            
            r['doc'] = doc
            _sc_lst.append(r)
        
        return _sc_lst
    
    def fn_clear_cflag(self):
        sc_ids = map(int, self.req.psv_ustr('sc_ids').split('|'))
        docs = self.get_docs_by_sc_ids(sc_ids, True)
        
        cur = self.cur()
        c = 0
        for r in docs:
            gjs = json.loads(r['doc'][7])
            ijs = json.loads(r['doc'][8])
            crc = gjs.get('crc')
            items_crc = gjs.get('items_crc')

            if r['sc_flag'] & REC_FLAG_PARTIAL:
                if r['doc_ijs_crc'] != items_crc: continue

                doc_ijs = json.loads(r['doc_ijs'])
                for t in doc_ijs: t['qty'] = t['r_qty']
                p_ijs = doc_ijs

                cur.execute('update schedule set sc_rev=sc_rev+1,sc_flag=sc_flag&(~%s),doc_crc=%s,doc_cur_ijs=%s where sc_id=%s and sc_rev=%s and sc_flag&%s!=0', (
                    REC_FLAG_CHANGED, crc, json.dumps(p_ijs, separators=(',',':')), r['sc_id'], r['sc_rev'], REC_FLAG_ACCEPTED
                ))
            else:
                p_ijs = ijs

                cur.execute('update schedule set sc_rev=sc_rev+1,sc_flag=sc_flag&(~%s),doc_crc=%s,doc_ijs_crc=%s,doc_cur_ijs=%s where sc_id=%s and sc_rev=%s and sc_flag&%s!=0', (
                    REC_FLAG_CHANGED, crc, items_crc, json.dumps(p_ijs, separators=(',',':')), r['sc_id'], r['sc_rev'], REC_FLAG_ACCEPTED
                ))
            if cur.rowcount > 0: c += 1
    
        if c: self.inc_seq()
        i_warning_s = None
        if len(sc_ids) != c: i_warning_s = '%d out of %d updated' % (c, len(sc_ids))
        
        self.req.writejs({'err': 0, 'i_warning_s': i_warning_s})
    fn_clear_cflag.PERM = DELIVERY_MGR_PERM
    
    def fn_accept(self):
        sc_ids = map(int, self.req.psv_ustr('sc_ids').split('|'))
        docs = self.get_docs_by_sc_ids(sc_ids, True)
        
        cur = self.cur()
        d_notes = []
        c = 0
        for r in docs:
            gjs = json.loads(r['doc'][7])
            ijs = json.loads(r['doc'][8])
            crc = gjs.get('crc')
            items_crc = gjs.get('items_crc')

            if r['sc_flag'] & REC_FLAG_PARTIAL:
                if r['doc_ijs_crc'] != items_crc: continue

                doc_ijs = json.loads(r['doc_ijs'])
                for t in doc_ijs: t['qty'] = t['r_qty']
                p_ijs = doc_ijs

                cur.execute('update schedule set sc_rev=sc_rev+1,sc_flag=sc_flag|%s,doc_crc=%s,doc_cur_ijs=%s where sc_id=%s and sc_rev=%s and sc_flag&%s=0', (
                    REC_FLAG_ACCEPTED, crc, json.dumps(p_ijs, separators=(',',':')), r['sc_id'], r['sc_rev'], REC_FLAG_ACCEPTED | REC_FLAG_CANCELLING
                ))
            else:
                p_ijs = ijs

                cur.execute('update schedule set sc_rev=sc_rev+1,sc_flag=sc_flag|%s,doc_crc=%s,doc_ijs_crc=%s,doc_cur_ijs=%s where sc_id=%s and sc_rev=%s and sc_flag&%s=0', (
                    REC_FLAG_ACCEPTED, crc, items_crc, json.dumps(p_ijs, separators=(',',':')), r['sc_id'], r['sc_rev'], REC_FLAG_ACCEPTED | REC_FLAG_CANCELLING
                ))
            if cur.rowcount > 0:
                c += 1
                m,d = divmod(r['sc_date'], 100)
                y,m = divmod(m, 100)
                d_notes.append([r['doc_type'],
                                r['doc_sid'],
                                'Schedule[%d] (%02d/%02d/%02d) - Accepted' % (r['sc_id'], m, d, y)
                ])
    
        if c:
            if d_notes: self.add_notes(d_notes)
            self.inc_seq()
            
        i_warning_s = None
        if len(sc_ids) != c: i_warning_s = '%d out of %d updated' % (c, len(sc_ids))
        
        self.req.writejs({'err': 0, 'i_warning_s': i_warning_s})
    fn_accept.PERM = DELIVERY_MGR_PERM
    
    def fn_set_zone_state(self):
        date = self.req.psv_int('date')
        zidx = self.req.psv_int('zidx')
        state = self.req.psv_int('state')
        if zidx < 1 or zidx >= len(ZONES) or state not in (0, -1, 1): return
        
        m,d = divmod(date, 100)
        y,m = divmod(m, 100)
        dto = datetime.date(y, m, d)
        if dto < datetime.date.today(): self.req.exitjs({'err': -9, 'err_s': "Invalid Date"})
        
        cur = self.cur()
        cur.execute('insert into schedule_special values(%s,%s,%s) on duplicate key update ss_val=%s', (
            date, zidx, state, state
            )
        )
        err = int(cur.rowcount <= 0)
        if not err:
            self.inc_seq()
        
        self.req.writejs({'err': err})
    fn_set_zone_state.PERM = DELIVERY_MGR_PERM
    
    def fn_get_overview(self):
        clerk_id = self.qsv_int('clerk_id')
        
        odt = datetime.date.today()
        cdt = odt.year * 10000 + odt.month * 100 + odt.day
        
        d_ss = {}
        cur = self.cur()
        cur.execute('select ss_date,ss_zidx,ss_val from schedule_special where ss_date>=%s', (cdt,))
        for r in cur.fetchall(): d_ss[ (r[0] << 26) | r[1] ] = r[2]
        
        d_dt = {}
        for r in self.get_docs(cdt, -1, clerk_id, 1):
            r['cid'] = r['cid'] != None and str(r['cid']) or ''
            r['doc_sid'] = str(r['doc_sid'])
            
            zid = r['zone_id']
            d = d_dt.setdefault(r['sc_date'], [None,] * len(ZONES))
            if not d[zid]: d[zid] = [0, 0, 0, 0, 0, 0]
            d = d[zid]
            
            sc_flag = r['sc_flag']
            if sc_flag & REC_FLAG_CANCELLING:
                d[3] += 1
            elif sc_flag & REC_FLAG_RESCHEDULED:
                d[2] += 1
            elif sc_flag & REC_FLAG_PARTIAL_CHANGED:
                d[5] += 1
            elif sc_flag & REC_FLAG_CHANGED:
                d[4] += 1
            elif sc_flag & REC_FLAG_ACCEPTED:
                d[1] += 1
            else:
                d[0] += 1
        
        l_dt = d_dt.items()
        l_dt.sort(key=lambda f_x: f_x[0])
        for dt,dd in l_dt:
            za = [0, 0, 0, 0, 0, 0]
            for z in dd:
                if not z: continue
                for i in range(len(z)): za[i] += z[i] or 0
            dd.insert(0, za)
        
        dt_1 = datetime.timedelta(1)
        n_dt = []
        sdt = odt
        max_days = MAX_DAYS
        for i in range(len(l_dt)):
            dt,dd = l_dt[i]
            m,d = divmod(dt, 100)
            y,m = divmod(m, 100)
            ndt = datetime.date(y, m, d)
            
            if max_days > 0:
                for j in range((ndt - sdt).days):
                    wd = sdt.weekday()
                    if wd != 6:
                        max_days -= 1
                        n_dt.append( (sdt.strftime("%a (%m/%d)"), None, wd, sdt.year  * 10000 + sdt.month * 100 + sdt.day) )
                        if max_days <= 0: break
                    sdt = sdt + dt_1
            wd = ndt.weekday()
            if wd != 6: max_days -= 1
            n_dt.append( (ndt.strftime("%a (%m/%d)"), dd, wd, ndt.year  * 10000 + ndt.month * 100 + ndt.day) )
            sdt = ndt + dt_1
            
        while max_days > 0:
            wd = sdt.weekday()
            if wd != 6:
                max_days -= 1
                n_dt.append( (sdt.strftime("%a (%m/%d)"), None, wd, sdt.year  * 10000 + sdt.month * 100 + sdt.day) )
            sdt = sdt + dt_1
        
        zones = [ (0, [0,] * len(n_dt)) ]
        for j in range(len(ZONES)):
            z,s = ZONES[j][:2]
            f = [0,] * len(n_dt)
            zones.append( (0, f) )
            for i in range(len(n_dt)):
                ss = d_ss.get((n_dt[i][3] << 26) | j)
                if ss != None:
                    f[i] = ss
                elif n_dt[i][2] in s:
                    f[i] = 1
        
        self.req.writejs({'dt': n_dt, 'zones': zones})


    def fn_get_cust_docs(self):
        cid = self.req.qsv_int('cid')
        fdt = datetime.date.today() - datetime.timedelta(30)
        fdt = fdt.year * 10000 + fdt.month * 100 + fdt.day
        
        self.req.writejs(self.get_full_docs(fdt, None, cid))

    def fn_get_nd_sc_docs(self):
        fdt = datetime.date.today() - datetime.timedelta(15)
        fdt = fdt.year * 10000 + fdt.month * 100 + fdt.day
        tdt = datetime.date.today() - datetime.timedelta(1)
        tdt = tdt.year * 10000 + tdt.month * 100 + tdt.day
        
        sc_lst = []
        for r in self.get_full_docs(fdt, tdt, None):
            if r['dr']: continue
            sc_lst.append(r)
        
        self.req.writejs({'lst': sc_lst})

    def get_full_docs(self, fdt, tdt, cid=None):
        so_sids = set()
        rc_sids = set()
        sc_lst = []
        
        d_user = dict([ (f_u[0], f_u[1]) for f_u in self.getuserlist() ])
        
        cur = self.cur()
        
        ws = []
        if fdt != None: ws.append('sc_date >= %d' % (fdt, ))
        if tdt != None: ws.append('sc_date <= %d' % (tdt, ))
        if ws:
            ws = ' where ' + ' and '.join(ws)
        else:
            ws = ''
        cur.execute('select sc_id,sc_date,sc_flag,doc_type,doc_sid,doc_crc,sc_note,(sc_flag&1) as is_accepted,(select count(*) from schedule where doc_type=sa.doc_type and doc_sid=sa.doc_sid) as dup_count from schedule sa'+ws+' order by sc_id desc')
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            sc_lst.append(r)
            if r['doc_type']:
                rc_sids.add(r['doc_sid'])
            else:
                so_sids.add(r['doc_sid'])

        d_so = {}
        if so_sids:
            cur.execute('select sid,status,sonum,clerk,sodate,global_js,cust_sid from sync_salesorders where'+(cid != None and ' cust_sid=%d and' % (cid,) or '')+' sid in (%s)' % (','.join(map(str, so_sids)), ))
            for r in cur.fetchall(): d_so[r[0]] = r
            
        d_rc = {}
        if rc_sids:
            cur.execute('select sid,type,num,assoc,order_date,global_js,cid from sync_receipts where'+(cid != None and ' cid=%d and' % (cid,) or '')+' sid in (%s)' % (','.join(map(str, rc_sids)), ))
            for r in cur.fetchall(): d_rc[r[0]] = r


        _sc_lst = sc_lst
        sc_ids = set()
        sc_lst = []
        for r in _sc_lst:
            if r['doc_type']:
                doc = d_rc.get(r['doc_sid'])
            else:
                doc = d_so.get(r['doc_sid'])
            if not doc: continue
            sc_lst.append(r)
            
            gjs = json.loads(doc[5])
            cust = gjs['customer'] or {}
            r['doc']  = doc = {
                'num': doc[2],
                'assoc': doc[3],
                'date': doc[4],
                'amt': gjs.get('total') or 0,
                'company': cust.get('company') or cust.get('name') or '',
                'cid': str(doc[6])
            }
            
            r['doc_sid'] = str(r['doc_sid'])
            sc_ids.add(r['sc_id'])
            
        d_dr = {}
        if sc_ids:
            cur.execute('select dr.sc_id,dr.num,dr.driver_id,dr.delivered,d.ts from deliveryv2_receipt dr left join deliveryv2 d on dr.d_id=d.d_id where d.d_id is not null and dr.sc_id in (%s) order by d.d_id asc' % (
                ','.join(map(str, sc_ids)),
                )
            )
            cnz = cur.column_names
            for r in cur.fetchall():
                r = dict(zip(cnz, r))
                r['driver_nz'] = d_user.get(r['driver_id']) or 'UNK'
                d_dr.setdefault(r['sc_id'], []).append(r)

                tp = datetime.date.fromtimestamp(r['ts'])
                r['dt_i'] = tp.year * 10000 + tp.month * 100 + tp.day

        for r in sc_lst:
            dr = r['dr'] = d_dr.get(r['sc_id'], [])
            dc = 0
            for d in dr:
                if d['dt_i'] == r['sc_date']: dc += 1
            r['delivery_count'] = dc
        
        return sc_lst

    CUST_LKU_KEYS = ('company', 'name', 'addr1', 'city', 'phone')
    def gen_lku(self, cust):
        l = set()
        for k in self.CUST_LKU_KEYS:
            v = cust.get(k)
            if v: l.add(v.lower())
        return l

    def get_docs(self, date, zone_id, clerk_id, mode=0, sort_reg=0, pending_only=0, dup_chk=0):
        clerk = None
        if clerk_id:
            clerk = self.finduser(clerk_id)
            if not clerk: return None

        so_sids = set()
        rc_sids = set()
        sc_lst = []
        cur = self.cur()
        if mode:
            addqs = ''
            where = ' where sc_date>=%s' + (pending_only and ' and sc_flag&%d=0' % (REC_FLAG_ACCEPTED,) or '')
        else:
            addqs = ',length(sc_note) as sc_note_len'
            where = ' where sc_date=%s' + (pending_only and ' and sc_flag&%d=0' % (REC_FLAG_ACCEPTED,) or '') + ' order by '+ (sort_reg and 'sc_id asc' or 'sc_id desc')
        sql_dup_chk = ''
        if dup_chk: sql_dup_chk = ',(select count(*) from schedule sb where sb.doc_type=sa.doc_type and sb.doc_sid=sa.doc_sid) as doc_dup'
        cur.execute('select sc_id,sc_date,sc_flag,doc_type,doc_sid,doc_crc,doc_ijs_crc,(sc_flag&1) as is_accepted' + sql_dup_chk + addqs + ' from schedule sa ' + where, (date,))
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            sc_lst.append(r)
            if r['doc_type']:
                rc_sids.add(r['doc_sid'])
            else:
                so_sids.add(r['doc_sid'])
        
        d_so = {}
        if so_sids:
            sql = 'select sid,sonum,clerk,sodate,global_js,cust_sid from sync_salesorders where sid in (%s)' % (','.join(map(str, so_sids)), )
            if clerk:
                cur.execute(sql + ' and clerk=%s', (clerk[1].lower(),))
            else:
                cur.execute(sql)
            for r in cur.fetchall(): d_so[r[0]] = r
            
        d_rc = {}
        if rc_sids:
            sql = 'select sid,num,assoc,order_date,global_js,cid from sync_receipts where sid_type=0 and sid in (%s)' % (','.join(map(str, rc_sids)), )
            if clerk:
                cur.execute(sql + ' and assoc=%s', (clerk[1].lower(),))
            else:
                cur.execute(sql)
            for r in cur.fetchall(): d_rc[r[0]] = r
        
        locs = set()
        _sc_lst = []
        for r in sc_lst:
            if r['doc_type']:
                doc_data = d_rc.get(r['doc_sid'])
            else:
                doc_data = d_so.get(r['doc_sid'])
            if not doc_data: continue
            _sc_lst.append(r)
            
            r['doc_data'] = doc_data
            doc_js = r['doc_js'] = json.loads(doc_data[4])
            doc_loc = None
            if doc_js['shipping']:
                doc_loc = doc_js['shipping'].get('loc')
            elif doc_js['customer']:
                doc_loc = doc_js['customer'].get('loc')

            r['doc_loc'] = doc_loc
            if doc_loc != None:
                doc_loc_dc = r['doc_loc_dc'] = base64.b64decode(doc_loc)
                locs.add(doc_loc_dc)
        
        sc_lst = _sc_lst
        
        d_loc = {}
        if locs:
            cur.execute('select loc,zone_id,lat,lng from address where loc in ('+','.join(['%s'] * len(locs))+') and flag=1', tuple(locs))
            for r in cur.fetchall(): d_loc[ r[0] ] = (r[1], str(r[2]), str(r[3]))
        
        lst = []
        for r in sc_lst:
            zid = 0
            geo = None
            if r['doc_loc'] != None: geo = d_loc.get(r['doc_loc_dc'])
            zid = geo and geo[0] or 0
            if zone_id >= 0 and zid != zone_id: continue
            
            gjs = doc_js = r['doc_js']
            doc_data = r['doc_data']

            r['doc_geo'] = geo
            r['zone_id'] = zid
            cust = doc_js['customer'] or {}
            r['cust_nz'] = cust.get('company') or cust.get('name') or ''
            #r['cid'] = doc_data[5] != None and str(doc_data[5]) or ''
            r['cid'] = doc_data[5]
            r['num'] = doc_data[1]
            r['doc_assoc'] = doc_data[2]
            r['doc_date'] = doc_data[3]
            r['doc_amt'] = doc_js['total']
            

            items_crc = gjs.get('items_crc')
            if r['sc_flag'] & REC_FLAG_PARTIAL and r['doc_ijs_crc'] != items_crc: r['sc_flag'] |= REC_FLAG_PARTIAL_CHANGED
            
            crc = gjs.get('crc')
            if r['sc_flag'] & REC_FLAG_ACCEPTED and r['doc_crc'] != crc: r['sc_flag'] |= REC_FLAG_CHANGED

            lku = self.gen_lku(cust)
            if doc_js['shipping']: lku.update( self.gen_lku(doc_js['shipping']) )
            lku.add(str(r['num']))
            r['lku'] = ' ' + ','.join(lku) + ' '

            r['doc_js'] = r['doc_data'] = r['doc_loc_dc'] = None
            #r['doc_sid'] = str(r['doc_sid'])
            
            lst.append(r)
    
        return lst
        
    def fn_get_docs(self):
        dt = self.qsv_int('dt')
        zone_id = self.qsv_int('zone_id')
        clerk_id = self.qsv_int('clerk_id')
        sort_reg = self.qsv_int('sort_reg')
        pending_only = self.qsv_int('pending_only')
        if zone_id >= len(ZONES): return
        
        m,d = divmod(dt, 100)
        y,m = divmod(m, 100)
        date = datetime.date(y, m, d)
        if date < datetime.date.today(): self.req.exitjs({'err': -9, 'err_s': "Invalid Date"})
        
        cur = self.cur()
        
        ss = 0
        if zone_id > 0:
            cur.execute('select ss_val from schedule_special where ss_date=%s and ss_zidx=%s', (dt, zone_id))
            rows = cur.fetchall()
            if rows:
                ss = rows[0][0]
            elif date.weekday() in ZONES[zone_id][1]:
                ss = 1
        
        sc_ids = set()
        lst = self.get_docs(dt, zone_id, clerk_id, 0, sort_reg, pending_only, 1)
        for r in lst:
            r['cid'] = r['cid'] != None and str(r['cid']) or ''
            r['doc_sid'] = str(r['doc_sid'])
            sc_ids.add(r['sc_id'])

        d_user = dict([ (f_u[0], f_u[1]) for f_u in self.getuserlist() ])
        d_dr = {}
        if sc_ids:
            cur.execute('select dr.sc_id,dr.num,dr.driver_id,dr.delivered,d.ts from deliveryv2_receipt dr left join deliveryv2 d on dr.d_id=d.d_id where d.d_id is not null and dr.sc_id in (%s) order by d.d_id asc' % (
                ','.join(map(str, sc_ids)),
                )
            )
            cnz = cur.column_names
            for r in cur.fetchall():
                r = dict(zip(cnz, r))
                r['driver_nz'] = d_user.get(r['driver_id']) or 'UNK'
                d_dr.setdefault(r['sc_id'], []).append(r)

                tp = datetime.date.fromtimestamp(r['ts'])
                r['dt_i'] = tp.year * 10000 + tp.month * 100 + tp.day
        
        for r in lst:
            dr = r['dr'] = d_dr.get(r['sc_id'], [])
            dc = 0
            for d in dr:
                if d['dt_i'] == r['sc_date']: dc += 1
            r['delivery_count'] = dc
        
        self.req.writejs({
            'state': ss,
            'date': dt,
            'zone_nz': zone_id < 0 and 'All' or ZONES[zone_id][0],
            'zone_id': zone_id,
            'lst': lst
        })

    def int2date(self, v):
        m,d = divmod(v, 100)
        y,m = divmod(m, 100)
        return datetime.date(y, m, d)

    def fn_print(self):
        sc_ids = map(int, self.req.psv_ustr('sc_ids').split('|'))
        view_only = self.qsv_int('view_only')
        if view_only and len(sc_ids) != 1: return
        
        cur = self.cur()
        docs = self.get_docs_by_sc_ids(sc_ids, True)
        for r in docs:
            dr = dict(zip(('cid','flag','num','assoc','cashier','doc_date','gjs','ijs'), r['doc'][1:]))
            gjs = dr['gjs'] = json.loads(dr['gjs'])
            ijs = dr['ijs'] = json.loads(dr['ijs'])
            dr['doc_date'] = time.strftime("%m/%d/%Y", time.localtime(dr['doc_date']))
            r.update(dr)
            r['is_accepted'] = bool(r['sc_flag'] & REC_FLAG_ACCEPTED)
            sc_date_o = self.int2date(r['sc_date'])
            r['sc_date_s'] = sc_date_o.strftime("%m/%d/%Y")
            r['sc_date_wd'] = sc_date_o.weekday()
            
            type_s = ''
            count_s = ''
            if r['doc_type']:
                d_type = (r['flag'] >> 8) & 0xFF
                d_status = (r['flag'] >> 0) & 0xFF
                
                if d_type >= 0 and d_type < len(ORD_TYPE):
                    type_s = ORD_TYPE[d_type]
                else:
                    type_s = 'UNK'
                    
                if d_status == 1:
                    type_s += ' - Reversed'
                elif d_status == 2:
                    type_s += ' - Reversing'
                    
                count_s = 'Item %d, Qty %d' % (gjs['itemcount'], int(gjs['qtycount']))
            else:
                if (r['flag'] >> 8) & 0xFF:
                    type_s = 'UNK - '
                else:
                    type_s = 'SO - '
                s = r['flag'] & 0xFF
                if s == 0:
                    type_s += 'Open'
                elif s == 1:
                    type_s += 'Close'
                elif s == 2:
                    type_s += 'Pending'
                if (r['flag'] >> 16) & 0xFF: type_s += ' - **Deleted**'
            
                count_s = 'Item %d, Qty %d' % (gjs['itemcount'], int(gjs['qtycount']))
            
            if r['sc_flag'] & REC_FLAG_RESCHEDULED:
                rsc_dt_o = self.int2date(r['sc_new_date'])
                r['rescheduling'] = (rsc_dt_o.strftime("%m/%d/%Y"), rsc_dt_o.weekday())
                
            items_crc = gjs.get('items_crc')
            if r['sc_flag'] & REC_FLAG_PARTIAL and r['doc_ijs_crc'] != items_crc: r['sc_flag'] |= REC_FLAG_PARTIAL_CHANGED
            
            crc = gjs.get('crc')
            if r['sc_flag'] & REC_FLAG_ACCEPTED and r['doc_crc'] != crc: r['sc_flag'] |= REC_FLAG_CHANGED
            
            r['diff_ijs'] = []
            if r['sc_flag'] & REC_FLAG_PARTIAL:
                r['mode'] = 1
                doc_ijs = r['doc_ijs'] and json.loads(r['doc_ijs']) or []
                if r['sc_flag'] & REC_FLAG_PARTIAL_CHANGED:
                    r['diff_ijs'] = self.diff_items(ijs, doc_ijs)

                    doc_ijs,r['unmatched'] = self.map_item(ijs, doc_ijs)
                    for i in range(len(ijs)):
                        ijs[i]['qty'] = doc_ijs[i]['qty']
                        if doc_ijs[i]['err'] == 1: ijs[i]['cmp_mode'] = 2
                else:
                    for i in range(len(ijs)): ijs[i]['qty'] = doc_ijs[i]['r_qty']

                    if r['sc_flag'] & REC_FLAG_CHANGED and r['doc_cur_ijs'] != None:
                        doc_cur_ijs = json.loads(r['doc_cur_ijs'])
                        r['diff_ijs'] = self.diff_items(ijs, doc_cur_ijs)

                n_total = 0
                t_item_sid = set()
                t_item_qty = 0
                n_ijs = []
                for i in range(len(ijs)):
                    t = ijs[i]
                    if not t['qty']: continue
                    n_ijs.append(t)
                    t_item_qty += abs(t['qty'])
                    t_item_sid.add(t['itemsid'])
                    if t['itemsid'] != 1000000005: n_total += t['qty'] * t['pricetax']

                ijs = r['ijs'] = n_ijs
                n_total *= (100 - gjs['discprc']) / 100.0
                
                gjs['n_total'] = n_total
                count_s = 'Item %d, Qty %d' % (len(t_item_sid), t_item_qty)
            
            elif r['sc_flag'] & REC_FLAG_CHANGED and r['doc_cur_ijs'] != None:
                doc_cur_ijs = json.loads(r['doc_cur_ijs'])
                r['diff_ijs'] = self.diff_items(ijs, doc_cur_ijs)

            r['type_s'] = type_s
            r['count_s'] = count_s
            
            loc = None
            if gjs['shipping']:
                loc = gjs['shipping'].get('loc')
            elif gjs['customer']:
                loc = gjs['customer'].get('loc')
                
            zidx = 0
            if loc != None:
                cur.execute('select zone_id from address where loc=%s and flag=1', (base64.b64decode(loc),))
                rr = cur.fetchall()
                if rr: zidx = rr[0][0]
            r['zone_nz'] = ZONES[zidx][0]
            
            if view_only:
                r['notes'] = d_notes = []
                cur.execute('select dn_ts,dn_flag,dn_val,(select user_name from user where user_id=dn_uid limit 1) as dn_unz from doc_note where doc_type=%s and doc_sid=%s order by dn_id desc limit 20', (
                    r['doc_type'], r['doc_sid']
                    )
                )
                for rr in cur.fetchall():
                    rr = list(rr)
                    rr[0] = time.strftime("%m/%d/%y %I:%M %p", time.localtime(rr[0]))
                    d_notes.append(rr)
                    
        r = {
            'REC_FLAG_PARTIAL_CHANGED': REC_FLAG_PARTIAL_CHANGED,
            'REC_FLAG_CANCELLING': REC_FLAG_CANCELLING,
            'REC_FLAG_RESCHEDULED': REC_FLAG_RESCHEDULED,
            'REC_FLAG_CHANGED': REC_FLAG_CHANGED,
            'has_perm_delivery_mgr': self.user_lvl & DELIVERY_MGR_PERM,
            'view_only': view_only,
            'auto_print': self.qsv_int('auto_print'),
            'round_ex': config.round_ex,
            'sc_docs': docs,
            'cts_s': time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime())
        }
        
        self.req.writefile('schedule_batch_print.html', r)
        
    
    def fn_map(self):
        dt = self.qsv_int('dt')
        r = {
            'has_perm_delivery_mgr': self.user_lvl & DELIVERY_MGR_PERM,
            'REC_FLAG_CANCELLING': REC_FLAG_CANCELLING,
            'REC_FLAG_ACCEPTED': REC_FLAG_ACCEPTED,
            'REC_FLAG_RESCHEDULED': REC_FLAG_RESCHEDULED,
            'REC_FLAG_CHANGED': REC_FLAG_CHANGED,
            'REC_FLAG_DUPLICATED': REC_FLAG_DUPLICATED,
            'REC_FLAG_R_RESCHEDULED': REC_FLAG_R_RESCHEDULED,
            'REC_FLAG_PARTIAL': REC_FLAG_PARTIAL,
            'REC_FLAG_PARTIAL_CHANGED': REC_FLAG_PARTIAL_CHANGED,
            'dt': self.qsv_int('dt'),
        }
        
        self.req.writefile('map_schedule.html', r)



    