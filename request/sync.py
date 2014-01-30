import json
import os
import time
import config
import re
import datetime
import traceback

DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_get_item(self):
        item_no = self.qsv_int('item_no')
        cur = self.cur()
        cur.execute('select sid,num,name,detail from sync_items where num=%s', (item_no,))
        rows = cur.fetchall()
        if not rows: return
        row = list(rows[0])
        row[0] = str(row[0])
        row[3] = json.loads(row[3])
        
        self.req.writejs(row)
    
    regx_kw = re.compile(u'[^ 0-9a-z,]+', re.I|re.M|re.S)
    def fn_itemsearch(self):
        kw = self.qsv_str('term')
        if not kw: return
        mode = self.qsv_int('mode')
        
        kws = set(self.regx_kw.sub(u' ', kw).strip().lower().replace(u',', u' ').strip().split(u' '))
        kws.discard(u'')
        if not kws: return
        
        db = self.db()
        cur = db.cur()
        
        sid_lku = {}
        items = []
        if kw.isdigit():
            cur.execute('select i.sid,i.num,i.name,i.detail,u.default_uom_idx from sync_items_upcs u left join sync_items i on (u.sid=i.sid) where u.upc=%d order by i.num asc limit 10' % (int(kw),))
            for x in cur.fetchall():
                sid_lku[ x[0] ] = True
                items.append( [str(x[0]),] + list(x[1:]) )
        
        if mode:
            kw = '+' + u' +'.join([k for k in kws])
        else:
            kw = '+' + u' +'.join([k + '* ' + k for k in kws])
        qs = "select sid,num,name,detail,(match(lookup,name) against (%s in boolean mode) + match(lookup) against (%s in boolean mode)*2) as pos from sync_items where match(lookup,name) against (%s in boolean mode) order by pos desc,num asc limit 10"
        cur.execute(qs, (kw, kw.replace(u'+', u''), kw))
        k = min(len(items), 2)
        for x in cur.fetchall():
            if sid_lku.has_key(x[0]): continue
            items.append( [str(x[0]),] + list(x[1:4]) + [None] )
            k += 1
            if k >= 10: break
        
        self.req.writejs(items)
        
    def fn_custsearch(self):
        kw = self.qsv_str('term')
        if not kw: return
        mode = self.qsv_int('mode')
        
        kws = set(self.regx_kw.sub(u' ', kw).strip().lower().replace(u',', u' ').strip().split(u' '))
        kws.discard(u'')
        if not kws: return
        
        db = self.db()
        cur = db.cur()
        #kw = db.escape_string('+' + u' +'.join([ len(k) > 2 and not k.isdigit() and k + '*' or k + '* ' + k for k in kws]).encode('utf8'))
        if mode:
            kw = '+' + u' +'.join([k for k in kws])
        else:
            kw = '+' + u' +'.join([k + '* ' + k for k in kws])
        qs = "select sid,name,detail,(match(name,lookup) against (%s in boolean mode) + match(name) against (%s in boolean mode)*2) as pos from sync_customers where match(name,lookup) against (%s in boolean mode) order by pos desc,sid desc limit 10"
        #self.out.write(qs)
        cur.execute(qs, (kw, kw.replace(u'+', u''), kw))
        res = [ [str(x[0]),] + list(x[1:]) for x in cur.fetchall()]
        
        self.req.writejs(res)

    def fn_sync(self):
        uts = self.getconfig(config.cid__sync_last_update)
        self.req.writejs({'sync': int(time.time()) - uts <= 7})
    
    def fn_getcustorders(self):
        cid = self.qsv_int('cid', None)
        if cid == None: return
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
    
        ord_flag = self.qsv_int('flag')
        
        if pgsz > 100 or eidx - sidx > 5: return
        
        db = self.db()
        cur = db.cur()
        
        rpg = {}
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select sso.sid,sso.status,sso.sonum,sso.clerk,sso.sodate,sso.global_js,so.delivery_date from sync_salesorders sso left join salesorder so on (sso.sid=so.sid) where sso.cust_sid=%d%s order by sso.sid desc limit %d,%d' % (
                cid, ord_flag == 0 and ' and sso.status=0' or '',
                sidx * pgsz, (eidx - sidx) * pgsz
                )
            )
            d = cur.fetchall()
            for i in range(sidx, eidx): rpg[i] = []
            if d:
                k = 0
                for r in d:
                    s = int(r[1])
                    g = json.loads(r[5])
                    customer = g['customer']
                    if r[6]:
                        m_r,m_day = divmod(r[6], 100)
                        m_year,m_month = divmod(m_r, 100)
                        m_mdy = '%02d/%02d/%04d' % (m_month, m_day, m_year)
                    else:
                        m_mdy = ''
                    r = [
                        r[2],
                        r[3],
                        g['qtycount'], g['sentcount'],
                        g['total'],
                        time.strftime("%m/%d/%Y", time.localtime(int(r[4]))),
                        m_mdy,
                        str(r[0])
                    ]
                    rpg[sidx].append(r)
                    k += 1
                    if k == pgsz:
                        sidx += 1
                        k = 0
        
        cur.execute('select count(*) from sync_salesorders where cust_sid=%d%s' % (
            cid, ord_flag == 0 and ' and status=0' or '',
            )
        )
        rlen = int(cur.fetchall()[0][0])
        
        self.req.writejs( {'res':{'len':rlen, 'rpg':rpg}} )
        
    
    ORDER_CLS = [None, ['po', 'purchaseorders'], ['so', 'salesorders']]
    def fn_getitemorders(self):
        rid = self.qsv_int('rid', None)
        if rid == None: return
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
    
        ord_type = self.qsv_int('type')
        cls = self.ORDER_CLS[ord_type]
        if not cls: return
        
        ord_flag = self.qsv_int('flag')
        
        if pgsz > 100 or eidx - sidx > 5: return
        
        db = self.db()
        cur = db.cur()
        
        rpg = {}
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select i.*,s.'+cls[0]+'num,s.clerk,s.'+cls[0]+'date from sync_link_item i left join sync_'+cls[1]+' s on (s.sid=i.doc_sid) where i.item_sid=%d and i.doc_type=%d%s order by i.doc_sid desc limit %d,%d' % (
                rid, ord_type, ord_flag == 0 and ' and i.flag=0' or '',
                sidx * pgsz, (eidx - sidx) * pgsz
                )
            )
            d = cur.fetchall()
            for i in range(sidx, eidx): rpg[i] = []
            if d:
                k = 0
                for r in d:
                    r = [
                        r[7], r[6], r[8],
                        int(r[4]), int(r[5]),
                        time.strftime("%m/%d/%Y", time.localtime(int(r[9]))),
                        str(r[1]), int(r[2])
                    ]
                    rpg[sidx].append(r)
                    k += 1
                    if k == pgsz:
                        sidx += 1
                        k = 0
        
        cur.execute('select count(*) from sync_link_item where item_sid=%d and doc_type=%d%s' % (
            rid, ord_type, ord_flag == 0 and ' and flag=0' or '',
            )
        )
        rlen = int(cur.fetchall()[0][0])
        
        self.req.writejs( {'res':{'len':rlen, 'rpg':rpg}} )
        
    def fn_printorder(self):
        rid = self.qsv_int('rid', None)
        if rid == None: return
    
        ord_type = self.qsv_int('type')
        
        if ord_type == 1:
            self.print_po(rid)
        elif ord_type == 2:
            self.print_so(rid)
        elif ord_type == 3:
            self.print_vo(rid)
            
    def print_po(self, rid):
        db = self.db()
        cur = db.cur()
        db_col_nzs = ('r_sid', 'r_vend_sid', 'r_status', 'r_ponum', 'r_clerk', 'r_podate', 'r_shipdate', 'r_duedate', 'r_creationdate', 'r_global', 'r_items')
        cur.execute('select * from sync_purchaseorders where sid=%d' % (rid,))
        r = cur.fetchall()
        if not r: return
        r = dict(zip(db_col_nzs, r[0]))
        
        r['r_status'] = int(r['r_status'])
        r['r_podate'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r['r_podate'])))
        r['r_creationdate'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r['r_creationdate'])))
        
        r['r_global'] = json.loads(r['r_global'])
        r['r_items'] = json.loads(r['r_items'])
        
        if r['r_global']['canceldate']:
            r['r_canceldate'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r['r_global']['canceldate'])))
        else:
            r['r_canceldate'] = ''
            
        r['auto_print'] = self.qsv_int('auto_print')
        
        r['round_ex'] = config.round_ex
        
        self.req.writefile('po_print_v2.html', r)
    
    def fn_has_salesorder(self):
        rno = self.req.qsv_ustr('rno')
        cur = self.cur()
        cur.execute('select sid from sync_salesorders where sonum=%s order by sid desc' % (rno,))
        rows = cur.fetchall()
        if not rows: return
        self.req.writejs({'sid': str(rows[0][0])})
    
    def print_so(self, rid):
        db = self.db()
        cur = db.cur()
        db_col_nzs = ('r_sid', 'r_cust_sid', 'r_status', 'r_price_level', 'r_sonum', 'r_clerk', 'r_cashier', 'r_sodate', 'r_duedate', 'r_creationdate', 'r_global', 'r_items')
        cur.execute('select * from sync_salesorders where sid=%d' % (rid,))
        r = cur.fetchall()
        if not r: return
        r = dict(zip(db_col_nzs, r[0]))
        
        r['r_price_level'] = int(r['r_price_level'])
        r['r_status'] = int(r['r_status'])
        r['r_sodate'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r['r_sodate'])))
        r['r_creationdate'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r['r_creationdate'])))
        
        r['r_global'] = json.loads(r['r_global'])
        r['r_items'] = json.loads(r['r_items'])
        
        r['auto_print'] = self.qsv_int('auto_print')
        
        cur.execute('select sid,sid_type,num from sync_receipts where so_sid=%s order by sid asc',(
            r['r_sid'],
            )
        )
        nzs = cur.column_names
        r['r_ref_receipts'] = [ dict(zip(nzs, f_row)) for f_row in cur.fetchall() ]
        
        r['r_delivery_date'] = ''
        cur.execute('select delivery_date,delivery_zip from salesorder where sid=%s and delivery_date!=0', (r['r_sid'],))
        rows = cur.fetchall()
        if rows:
            r_delivery_date = rows[0][0]
            m_r,m_day = divmod(r_delivery_date, 100)
            m_year,m_month = divmod(m_r, 100)
            r['r_delivery_date'] = "%02d/%02d/%04d" % (m_month, m_day, m_year)
            r['r_delivery_zip'] = '%05d' % rows[0][1]
        
        r['round_ex'] = config.round_ex
        r['price_lvls'] = config.PRICE_LEVELS
        
        self.req.writefile('so_print_v2.html', r)

    def print_vo(self, rid):
        db = self.db()
        cur = db.cur()
        db_col_nzs = ('r_sid', 'r_vend_sid', 'r_ref_sid', 'r_flag', 'r_num', 'r_clerk', 'r_voucherdate', 'r_duedate', 'r_invdate', 'r_creationdate', 'r_global', 'r_items')
        cur.execute('select * from sync_vouchers where sid=%d' % (rid,))
        r = cur.fetchall()
        if not r: return
        r = dict(zip(db_col_nzs, r[0]))
        
        r['r_flag'] = int(r['r_flag'])
        r['r_voucherdate'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r['r_voucherdate'])))
        r['r_creationdate'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r['r_creationdate'])))
        r['r_duedate'] = r['r_duedate'] and time.strftime("%m/%d/%Y", time.localtime(int(r['r_duedate']))) or ''
        r['r_invdate'] = r['r_invdate'] and time.strftime("%m/%d/%Y", time.localtime(int(r['r_invdate']))) or ''
        
        r['r_global'] = json.loads(r['r_global'])
        r['r_items'] = json.loads(r['r_items'])
        
        r['auto_print'] = self.qsv_int('auto_print')
        
        r['round_ex'] = config.round_ex
        
        porefs = {}
        for i in r['r_items']:
            if i['porefsid'] == None: continue
            porefs[ str(i['porefsid']) ] = True
            
        po = []
        if porefs:
            cur.execute('select sid,ponum,clerk,podate from sync_purchaseorders where sid in (%s) order by sid desc' % (','.join(porefs),))
            for i in cur.fetchall():
                po.append( [i[0],] + list(i[1:3]) + [time.strftime("%m/%d/%Y", time.localtime(int(i[3])))] )
        r['r_po'] = po
        
        self.req.writefile('vo_print_v2.html', r)
