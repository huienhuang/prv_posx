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


DEFAULT_PERM = SALES_PERM | DELIVERY_MGR_PERM
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
        
        cur = self.cur();
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
            cur.execute('update schedule set sc_flag=sc_flag|%s where sc_id=%s and sc_rev=%s and sc_flag&%s!=0', (
                REC_FLAG_CANCELLING, sc_id, r['sc_rev'], REC_FLAG_ACCEPTED
                )
            )
            d_note = 'Schedule[%d] (%02d/%02d/%02d) - Deleting, Waiting For Confirmation' % (r['sc_id'], m, d, y)
        else:
            cur.execute('delete from schedule where sc_id=%s and sc_rev=%s and sc_flag&%s=0', (
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
            cur.execute('delete from schedule where sc_id=%s and sc_flag&%s!=0', (
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
        company = (gjs.get('customer') or {}).get('company') or ''
        
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
            'crc': crc
        }
        
        cur.execute('select * from schedule where doc_type=%s and doc_sid=%s order by sc_id asc', (
            d_type, sid
            )
        )
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            
            if r['sc_flag'] & REC_FLAG_PARTIAL:
                doc_ijs = r['doc_ijs'] and json.loads(r['doc_ijs']) or []
                if r['doc_crc'] == crc:
                    r['doc_ijs'] = [ {'qty': f_i[3]} for f_i in doc_ijs ]
                else:
                    r['doc_ijs'],r['unmatched'] = self.map_item(ijs, doc_ijs)

            recs.append(r)
        
        self.req.writejs(js)
    
    def map_item(self, ijs, doc_ijs):
        d_items = {}
        for r in doc_ijs:
            if not r[3]: continue
            v = d_items.setdefault((r[0], r[1]), [0, {}])[1].setdefault(r[2], []).append(r[3])
            
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
            else:
                r['err'] = -1
        
        return (n_ijs, unmatched)
        
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
        
        if mode:
            r_crc,r_ijs = self.req.psv_js('doc')
            
            ijs = json.loads(ijs)
            if new_doc_crc != r_crc: self.req.exitjs({'err': -11, 'err_s': 'Doc Changed, CRC Error!'})
            
            ijs_note = []
            n_ijs = []
            for i in range(len(ijs)):
                r_item = r_ijs[i]
                item = ijs[i]
                r_qty = int(r_item[1])
                if int(r_item[0]) != item['itemsid'] or r_qty * item['qty'] < 0 or abs(r_qty) > abs(item['qty']):
                    self.req.exitjs({'err': -10, 'err_s': 'Item Unmatched!'})
                n_ijs.append([item['itemsid'], item['uom'], item['qty'], r_qty])
                if r_qty: ijs_note.append(u'> %d - %s - %s - %d / %d %s' % (item['itemno'], item['alu'], item['desc1'], r_qty, item['qty'], item['uom']))
            
            s_ijs = json.dumps(n_ijs, separators=(',',':'))
            
        if sc_id == 0:
            cur.execute('insert into schedule values(null,%s,0,1,%s,%s,%s,%s,%s,%s,%s)', (
                d_date, mode and REC_FLAG_PARTIAL or 0, prio, d_type, d_sid, new_doc_crc, note, mode and s_ijs or None
                )
            )
            sc_id = cur.lastrowid
            d_notes.append('Schedule[%d] (%s) - Created(Pending) - %s' % (sc_id, o_date.strftime('%m/%d/%y'), mode and 'Partial Delivery\n' + '\n'.join(ijs_note) or 'Complete Delivery'))
        else:
            cur.execute("select sc_flag,sc_date,sc_prio,sc_note,doc_crc,doc_ijs from schedule where sc_id=%s and sc_rev=%s", (
                sc_id, rev
                )
            )
            row = cur.fetchall()
            if not row: self.req.exitjs({'err': -3, 'err_s': "document #%s - record #%s - can't find the record" % (d_num, sc_id)})
            o_r = dict(zip(cur.column_names, row[0]))
            new_sc_flag = o_r['sc_flag']
            
            chg = False
            if o_r['sc_flag'] & REC_FLAG_CANCELLING: self.req.exitjs({'err': -2, 'err_s': "Cancellation is pending"})
            if o_r['sc_date'] != d_date or o_r['sc_prio'] != prio or o_r['sc_note'] != note: chg = True
            if bool(o_r['sc_flag'] & REC_FLAG_PARTIAL) != bool(mode):
                chg = True
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
                if new_doc_crc != o_r['doc_crc']:
                    m_note = chg = True
                    if not self.req.psv_int('check_n_confirm'): self.req.exitjs({'err': -12, 'err_s': "Document Changed! Please Check!"})
                    
                o_r['doc_ijs'] = o_r['doc_ijs'] and json.loads(o_r['doc_ijs']) or []
                if n_ijs != o_r['doc_ijs']:
                    chg = True
                    if [ f_x for f_x in n_ijs if f_x[3] ] != [ f_x for f_x in o_r['doc_ijs'] if f_x[3] ]:
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
            
            if o_r['sc_date'] != d_date:
                m,d = divmod(o_r['sc_date'], 100)
                y,m = divmod(m, 100)
                o_old_date = datetime.date(y, m, d)
                
                if o_r['sc_flag'] & REC_FLAG_ACCEPTED:
                    new_sc_flag |= REC_FLAG_RESCHEDULED
                    d_notes.append('Rescheduling[%d] From %s To %s, Waiting For Confirmation' % (sc_id, o_old_date.strftime('%m/%d/%y'), o_date.strftime('%m/%d/%y'), ))
                else:
                    d_notes.append('Reschedule[%d] From %s To %s' % (sc_id, o_old_date.strftime('%m/%d/%y'), o_date.strftime('%m/%d/%y'), ))
            
            if o_r['sc_flag'] & REC_FLAG_ACCEPTED:
                if o_r['sc_prio'] != prio or o_r['sc_note'] != note: new_sc_flag |= REC_FLAG_CHANGED
                cur.execute("update schedule set sc_rev=sc_rev+1,sc_flag=%s,sc_new_date=%s,sc_prio=%s,sc_note=%s,doc_crc=%s,doc_ijs=%s where sc_id=%s and sc_rev=%s", (
                    new_sc_flag, d_date, prio, note, new_doc_crc, mode and s_ijs or None, sc_id, rev
                    )
                )
            else:
                cur.execute("update schedule set sc_rev=sc_rev+1,sc_new_date=0,sc_flag=%s,sc_date=%s,sc_prio=%s,sc_note=%s,doc_crc=%s,doc_ijs=%s where sc_id=%s and sc_rev=%s", (
                    new_sc_flag,d_date, prio, note, new_doc_crc, mode and s_ijs or None, sc_id, rev
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
        docs = self.get_docs_by_sc_ids(sc_ids)
        
        cur = self.cur()
        c = 0
        for r in docs:
            if r['sc_flag'] & REC_FLAG_PARTIAL:
                cur.execute('update schedule set sc_rev=sc_rev+1,sc_flag=sc_flag&(~%s) where sc_id=%s and sc_flag&%s!=0', (
                    REC_FLAG_CHANGED, r['sc_id'], REC_FLAG_ACCEPTED
                ))
            else:
                crc = json.loads(r['doc'][2]).get('crc')
                cur.execute('update schedule set sc_rev=sc_rev+1,sc_flag=sc_flag&(~%s),doc_crc=%s where sc_id=%s and sc_flag&%s!=0', (
                    REC_FLAG_CHANGED, crc, r['sc_id'], REC_FLAG_ACCEPTED
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
            if r['sc_flag'] & REC_FLAG_PARTIAL:
                cur.execute('update schedule set sc_flag=sc_flag|%s,sc_rev=sc_rev+1 where sc_id=%s and sc_rev=%s and sc_flag&%s=0', (
                    REC_FLAG_ACCEPTED, r['sc_id'], r['sc_rev'], REC_FLAG_ACCEPTED | REC_FLAG_CANCELLING
                ))
            else:
                crc = json.loads(r['doc'][7]).get('crc')
                cur.execute('update schedule set sc_flag=sc_flag|%s,sc_rev=sc_rev+1,doc_crc=%s where sc_id=%s and sc_rev=%s and sc_flag&%s=0', (
                    REC_FLAG_ACCEPTED, crc, r['sc_id'], r['sc_rev'], REC_FLAG_ACCEPTED | REC_FLAG_CANCELLING
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
        
        so_sids = set()
        rc_sids = set()
        sc_lst = []
        
        d_user = dict([ (f_u[0], f_u[1]) for f_u in self.getuserlist() ])
        
        cur = self.cur()
        
        cur.execute('select sc_id,sc_date,sc_flag,doc_type,doc_sid,doc_crc,sc_note,(sc_flag&1) as is_accepted,(select count(*) from schedule sb where sb.doc_type=sa.doc_type and sb.doc_sid=sa.doc_sid) as doc_dup from schedule sa where sc_date>=%s order by sc_id desc', (fdt,))
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
            cur.execute('select sid,status,sonum,clerk,sodate,global_js from sync_salesorders where cust_sid=%s and sid in (%s)' % (cid, ','.join(map(str, so_sids)), ))
            for r in cur.fetchall(): d_so[r[0]] = r
            
        d_rc = {}
        if rc_sids:
            cur.execute('select sid,type,num,assoc,order_date,global_js from sync_receipts where cid=%s and sid_type=0 and sid in (%s)' % (cid, ','.join(map(str, rc_sids)), ))
            for r in cur.fetchall(): d_rc[r[0]] = r


        _sc_lst = sc_lst
        so_sids = {}
        rc_nums = set()
        sc_lst = []
        for r in _sc_lst:
            if r['doc_type']:
                doc = d_rc.get(r['doc_sid'])
            else:
                doc = d_so.get(r['doc_sid'])
            if not doc: continue
            sc_lst.append(r)
            
            gjs = json.loads(doc[5])
            r['doc']  = doc = {
                'num': doc[2],
                'assoc': doc[3],
                'date': doc[4],
                'amt': gjs.get('total') or 0
            }
            
            if r['doc_type']:
                rc_nums.add(doc['num'])
            else:
                r['nums'] = so_sids.setdefault(r['doc_sid'], [])
                
            r['doc_sid'] = str(r['doc_sid'])
            
        if so_sids:
            cur.execute('select so_sid,num from sync_receipts sr where sid_type=0 and so_type=0 and so_sid in (%s)' % (','.join(map(str, so_sids.keys())), ))
            for rr in cur.fetchall():
                so_sids[ rr[0] ].append(rr[1])
                rc_nums.add(rr[1])
        
        d_dr = {}
        if rc_nums:
            cur.execute('select dr.num,d.ts,dr.driver_id,dr.delivered from deliveryv2_receipt dr left join deliveryv2 d on (dr.d_id=d.d_id) where dr.num in (%s)' % (','.join(map(str, rc_nums)),))
            for r in cur.fetchall():
                r = list(r)
                r.append(0)
                tp = time.localtime(r[1])
                r[1] = tp.tm_year * 10000 + tp.tm_mon * 100 + tp.tm_mday
                d_dr.setdefault(r[0], []).append(r)
        
        for r in sc_lst:
            if not r['doc_type']: continue
            dr = []
            for d in d_dr.get(r['doc']['num']) or []:
                if d[1] == r['sc_date']:
                    d[-1] = 1
                    dr.append( (d_user.get(d[2]) or 'UNK', d[3]) )
            r['dr'] = dr
            
        for r in sc_lst:
            if r['doc_type']: continue
            dr = []
            for n in r['nums']:
                for d in d_dr.get(n) or []:
                    if not d[-1] and d[1] == r['sc_date']:
                        dr.append( (d_user.get(d[2]) or 'UNK', d[3], n) )
            r['dr'] = dr
        
        self.req.writejs(sc_lst)

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
        cur.execute('select sc_id,sc_date,sc_flag,doc_type,doc_sid,doc_crc,(sc_flag&1) as is_accepted' + sql_dup_chk + addqs + ' from schedule sa ' + where, (date,))
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
            
            doc_js = r['doc_js']
            doc_data = r['doc_data']

            r['doc_geo'] = geo
            r['zone_id'] = zid
            r['cust_nz'] = (doc_js['customer'] or {}).get('company') or ''
            #r['cid'] = doc_data[5] != None and str(doc_data[5]) or ''
            r['cid'] = doc_data[5]
            r['num'] = doc_data[1]
            r['doc_assoc'] = doc_data[2]
            r['doc_date'] = doc_data[3]
            r['doc_amt'] = doc_js['total']
            
            crc = doc_js.get('crc')
            if r['sc_flag'] & REC_FLAG_PARTIAL:
                if r['doc_crc'] != crc: r['sc_flag'] |= REC_FLAG_PARTIAL_CHANGED
            elif r['sc_flag'] & REC_FLAG_ACCEPTED:
                if r['doc_crc'] != crc: r['sc_flag'] |= REC_FLAG_CHANGED
                
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
        
        frm_ts = int(time.mktime(date.timetuple()))
        to_ts = int(time.mktime((date + datetime.timedelta(1)).timetuple()))
        
        rc_nums = set()
        so_sids = {}
        lst = self.get_docs(dt, zone_id, clerk_id, 0, sort_reg, pending_only, 1)
        for r in lst:
            if r['doc_type']:
                rc_nums.add(r['num'])
            else:
                r['nums'] = so_sids.setdefault(r['doc_sid'], [])
                
            r['cid'] = r['cid'] != None and str(r['cid']) or ''
            r['doc_sid'] = str(r['doc_sid'])
            
        if so_sids:
            cur.execute('select so_sid,num from sync_receipts sr where sid_type=0 and so_type=0 and so_sid in (%s)' % (','.join(map(str, so_sids.keys())), ))
            for rr in cur.fetchall():
                so_sids[ rr[0] ].append(rr[1])
                rc_nums.add(rr[1])
        
        d_dr = {}
        if rc_nums:
            cur.execute('select dr.num,dr.driver_id,dr.delivered from deliveryv2_receipt dr left join deliveryv2 d on (dr.d_id=d.d_id and d.ts>=%s and d.ts<%s) where dr.num in (%s) and d.d_id is not null' % (
                frm_ts, to_ts, ','.join(map(str, rc_nums))
                )
            )
            for r in cur.fetchall():
                r = list(r)
                r.append(0)
                d_dr.setdefault(r[0], []).append(r)
        
        d_user = dict([ (f_u[0], f_u[1]) for f_u in self.getuserlist() ])
        
        for r in lst:
            if not r['doc_type']: continue
            dr = []
            for d in d_dr.get(r['num']) or []:
                d[-1] = 1
                dr.append( (d_user.get(d[1]) or 'UNK', d[2]) )
            r['dr'] = dr
            r['delivery_count'] = len(dr)
            
        for r in lst:
            if r['doc_type']: continue
            dr = []
            for n in r['nums']:
                for d in d_dr.get(n) or []:
                    if not d[-1]:
                        dr.append( (d_user.get(d[1]) or 'UNK', d[2], n) )
            r['dr'] = dr
            r['delivery_count'] = len(dr)
        
        
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
            
            
            if r['sc_flag'] & REC_FLAG_PARTIAL:
                r['mode'] = 1
                doc_ijs = r['doc_ijs'] and json.loads(r['doc_ijs']) or []
                if r['doc_crc'] == gjs.get('crc'):
                    r['doc_ijs'] = [ {'qty': f_i[3]} for f_i in doc_ijs ]
                else:
                    r['doc_ijs'],r['unmatched'] = self.map_item(ijs, doc_ijs)
                
                n_total = 0
                t_item_sid = set()
                t_item_qty = 0
                n_ijs = []
                for i in range(len(r['doc_ijs'])):
                    t = r['doc_ijs'][i]
                    t_qty = t['qty']
                    if not t_qty: continue
                    n_t = ijs[i]
                    n_ijs.append(n_t)
                    t_item_qty += abs(t_qty)
                    t_item_sid.add(n_t['itemsid'])
                    n_t['qty'] = t_qty
                    if n_t['itemsid'] != 1000000005: n_total += t_qty * n_t['pricetax']
                ijs = r['ijs'] = n_ijs
                n_total *= (100 - gjs['discprc']) / 100.0
                
                gjs['n_total'] = n_total
                count_s = 'Item %d, Qty %d' % (len(t_item_sid), t_item_qty)
                
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



    