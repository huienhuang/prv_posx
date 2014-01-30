import json
import os
import time
import config
import re
import datetime


DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/basehandler').RequestHandler):

    def fn_default(self):
        self.req.writefile('receipttotal.html')

    PAYMENT_NAMES = ('none', 'cash', 'check', 'visa', 'debit', 'P5', 'account', 'P7', 'deposit', 'split')
    def fn_total(self):
        frm_date = self.qsv_int('from_date')
        to_date = self.qsv_int('to_date')
        
        if to_date - frm_date > 100 * 24 * 3600: return
        if to_date > 1346482800: return
        
        db = self.db()
        cur = db.cur()
        cur.execute('select * from sync_receipts where sid_type=0 and order_date >= %d and order_date < %d' % (frm_date, to_date))
        colnzs = ('sid', 'sid_type', 'rid', 'cid', 'so_sid', 'so_type', 'type', 'num', 'assoc', 'cashier', 'price_level', 'order_date', 'creation_date', 'global_js', 'items_js')
        
        receipts_by_cate = {}
        receipts = {}
        others = []
        total = total_tax = 0.0
        res = []
        idx_sid = {}
        for r in cur.fetchall():
            r = dict(zip(colnzs, r))
            res.append(r)
            idx_sid[ r['sid'] ] = True
        
        for r in res:
            global_js = json.loads(r['global_js'])
            
            mprc = (100 - global_js['discprc']) / 100
            rstatus = int(r['type']) & 0xFF
            rtype = (int(r['type']) >> 0x08) & 0xFF
            
            item_num = r['num']
            rec = receipts[ item_num ] = {
                'rtype':rtype,
                'rstatus':rstatus,
                'payment': self.PAYMENT_NAMES[ global_js['tendertype'] ],
                'origtaxedtotal':'%0.2f' % global_js['total'],
                'order_date': time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r['order_date']))),
                'customer': '',
                'total': 0,
                'taxedtotal' : 0,
                'sid': str(r['sid']),
                'status': '',
                'ref': str(r['rid'])
            }
            if rstatus == 2:
                rec['status'] = 'Return '
            elif rstatus == 1:
                rec['status'] = 'Cancel '
                
            if r['rid'] != None:
                cur.execute('select num from sync_receipts where sid_type=0 and sid=%s' % (r['rid'],))
                rec['status'] += str(cur.fetchall()[0][0])
                if idx_sid.has_key(r['rid']): rec['status'] += '*'
            
            customer = global_js['customer']
            if customer: rec['customer'] = customer['company'] or customer['name'] or ''
            if rtype > 1:
                others.append(item_num)
                continue
            
            r_total = r_total_tax = 0
            payment_on_account = False
            item_count = 0
            for t in json.loads(r['items_js']):
                if t['itemsid'] == 1000000005:
                    payment_on_account = True
                    continue
                
                price = t['price'] * t['qty'] * mprc
                price_tax = t['pricetax'] * t['qty'] * mprc
                
                if rtype > 0:
                    price = -price
                    price_tax = -price_tax
                    
                r_total += price
                r_total_tax += price_tax
            
            total += r_total
            total_tax += r_total_tax
            rec['total'] = '%0.2f' % r_total
            rec['taxedtotal'] = '%0.2f' % r_total_tax

            rec['tender_lst'] = t_lst = []
            cate = False
            if r_total_tax:
                t_total = 0
                for t in global_js['tender']:
                    if r_total_tax >= 0:
                        if t['amount'] < 0: continue
                    else:
                        if t['amount'] >= 0: continue
                
                    t_total += t['amount']
                    t_lst.append( (t['amount'], t['type']) )
                
                for t in t_lst:
                    rt = t[0] / t_total
                    
                    p_total = r_total * rt
                    p_total_tax = r_total_tax * rt
                    
                    cate = True
                    receipts_by_cate.setdefault( t[1], []).append((item_num, '%0.2f' % p_total, '%0.2f' % p_total_tax))
        
            if not cate: others.append(item_num)
        
        payments = []
        for k,v in receipts_by_cate.items():
            v.sort()
            payments.append( (self.PAYMENT_NAMES[k], v) )
        
        others.sort()
        
        total = {'total':'%0.2f' % total, 'taxedtotal':'%0.2f' % total_tax, 'receipts':receipts, 'payments':payments, 'others':others}
        self.req.writejs(total)

