import json
import os
import time
import config
import re
import datetime
import traceback
import sqlanydb
import bisect
import phonenum_parser

rex = config.round_ex

Receipt = App.load('/request/receipt')
Delivery = App.load('/request/delivery')
DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):

    PRICE_LEVELS = ['Regular Price', 'Wholesale 1', 'Wholesale 2', 'special', 'Dealer Price']
    
    OF_PAID = 1 << 8
    OF_PAYABLE = 1 << 16
    OF_CLOSE = 1 << 3
    OF_REVERSED = 1 << 2 #REVERSED Or Regular
    OF_REVERSING = 1 << 1 #REVERSING OR Regular
    OF_COMPLETED = 1 << 0
    
    def fn_default(self):
        d = {
            'USER_PERM_BIT': config.USER_PERM_BIT,
            'userlist': self.getuserlist(),
            'user_lvl': self.user_lvl,
            'user_name': self.user_name,
            'user_id': self.user_id,
            'price_lvls': self.PRICE_LEVELS,
            'order_id': self.qsv_int('order_id'),
            'load_type': self.qsv_int('load_type')
        }
        self.req.writefile('sorder.html', d)
    
    def get_rdb(self):
        return sqlanydb.connect(**config.sqlany_pos_server)
    
    def get_day_ts(self, ts):
        tp = time.localtime(ts or None)
        ts = int(time.mktime(datetime.date(tp.tm_year, tp.tm_mon, tp.tm_mday).timetuple()))
        return ts
    
    def fn_save(self):
        order = self.req.psv_js('js_sorder')
        order_id = int(order['order_id'])
        order_close = int(order['status'])
        assoc_id = int(order['associate_id']) or self.user_id
        price_level = int(order['price_level'])
        is_paid = int(order['is_paid'])
        c_total = round(float(order['total']), 2)
        customer_sid = None
        cur_order_id = 0
        res = { 'order_id': cur_order_id, 'err': None, 'associate_id': assoc_id, 'price_level': price_level, 'customer_sid': customer_sid }
        if order['customer']:
            customer_sid = int(order['customer']['sid'])
            res['customer_sid'] = str(customer_sid)
            
        if price_level < 0 or price_level >= len(self.PRICE_LEVELS):
            res['err'] = (-1, 'No Such Price Level %d' % price_level)
            self.req.exitjs(res)
            
        assoc = self.finduser(assoc_id)
        if not assoc or not int(assoc[2]):
            res['err'] = (-1, 'No Such User')
            self.req.exitjs(res)
            
        ord_creation_date = now_ts = int(time.time())
        ord_order_date = now_ts - self.get_day_ts(now_ts) + self.get_day_ts(int(order['date']))
        
        ord_items = items = order['items']
        if not len(items):
            res['err'] = (-1, 'No Items')
            self.req.exitjs(res)
        
        item_ids = {}
        qtycount = 0
        subtotal = 0.0
        k = -1
        for item in items:
            k += 1
            item['id'] = int(item['id'])
            item['num'] = int(item['num'])
            item['in_desc'] = item['in_desc'].strip()
            item['in_qty'] = int(item['in_qty'])
            item['in_price'] = round(float(item['in_price']), 2)
            if item['in_price'] < 0:
                res['err'] = (k, 'Negative Price')
                self.req.exitjs(res)
            in_extprice = round(item['in_qty'] * item['in_price'], 2)
            if in_extprice != item['in_extprice']:
                res['err'] = (k, 'Price Not Matched')
                self.req.exitjs(res)
            subtotal += item['in_extprice']
            in_uom_idx = item['in_uom_idx'] = int(item['in_uom_idx'])
            unit = item['units'][ in_uom_idx ]
            unit[0][price_level] = round(float(unit[0][price_level]), 2)
            unit[1] = unit[1].strip()
            unit[2] = unit[2].strip()
            unit[3] = round(float(unit[3]), 2)
            if not unit[3]:
                res['err'] = (k, 'Zero UnitFactor')
                self.req.exitjs(res)
            item['in_base_qty'] = item['in_qty'] * unit[3]
            if item.has_key('err'): del item['err']
            if item.has_key('prev_qty'): del item['prev_qty']
            qtycount += abs(item['in_qty'])
            item_ids[item['id']] = True
        
        itemcount = len(item_ids)
        disc = round(float(order['disc']), 2)
        subtotal = round(subtotal, 2)
        if order.has_key('disc_amt'):
            disc_amount = round(float(order['disc_amt']), 2)
        else:
            disc_amount = round(-subtotal * disc / 100.0, 2)
        total = round(subtotal + disc_amount, 2)
        
        if not (abs(total - c_total) <= 0.01001):
            res['err'] = (-1, 'Total Not Matched')
            res['total'] = total
            res['c_total'] = c_total
            self.req.exitjs(res)
        
        ord_flag = 0
        ord_paid_date = 0
        ord_comment = None
        if total > 0 and order_close:
            ord_flag = self.OF_PAYABLE | self.OF_CLOSE
            if is_paid:
                ord_flag |= self.OF_PAID
                ord_paid_date = now_ts
                ord_comment = 'Mark As Paid'
        elif order_close:
            ord_flag = self.OF_CLOSE
        
        db = self.db()
        cur = db.cur()
        
        customer = None
        if customer_sid != None:
            cur.execute('select sid,name,detail from sync_customers where sid=%d limit 1' % (customer_sid, ))
            row = cur.fetchall()
            if not row:
                res['err'] = (-1, 'Customer Not Found')
                self.req.exitjs(res)
            row = row[0]
            customer = json.loads(row[2])
            customer['sid'] = row[0]
            customer['name'] = row[1]
        
        ord_global = {
            'total': total,
            'subtotal': subtotal,
            'disc' : disc,
            'disc_amount': disc_amount,
            'itemcount': itemcount,
            'qtycount': qtycount,
            'memo': order['memo'][:512].strip(),
            'customer': customer
        }
        
        dbc = self.get_rdb()
        sur = dbc.cursor()
        
        try:
            if not self.check_item(sur, price_level, items, res): self.req.exitjs(res)
            
            if order_id <= 0:
                cur.execute("insert into sorder values(null,0,%d,%d,%d,%d,%d,%d,%d,0,%%s,%%s,%%s)" % (
                    ord_flag,
                    assoc_id,
                    self.user_id,
                    price_level,
                    ord_order_date,
                    ord_creation_date,
                    ord_paid_date,
                    ),
                    (
                    json.dumps(ord_global, separators=(',',':')),
                    json.dumps(ord_items, separators=(',',':')),
                    ''
                    #json.dumps(ord_comment, separators=(',',':'))
                    )
                )
                cur_order_id = cur.lastrowid or 0
                
            else:
                cur.execute("select ord_creation_date from sorder where ord_id=%d and ord_flag&%d=%d" % (order_id, self.OF_CLOSE, 0))
                rows = cur.fetchall()
                if rows:
                    ord_creation_date = rows[0][0]
                    cur.execute("update sorder set ord_flag=%d,ord_assoc_id=%d,ord_user_id=%d,ord_price_level=%d,ord_order_date=%d,ord_paid_date=%d,ord_rev=ord_rev+1,ord_global_js=%%s,ord_items_js=%%s,ord_comment_js=%%s where ord_id=%d and ord_flag&%d=%d" % (
                        ord_flag,
                        assoc_id,
                        self.user_id,
                        price_level,
                        ord_order_date,
                        ord_paid_date,
                        order_id,
                        self.OF_CLOSE,
                        0
                        ),
                        (
                        json.dumps(ord_global, separators=(',',':')),
                        json.dumps(ord_items, separators=(',',':')),
                        ''
                        #json.dumps(ord_comment, separators=(',',':')),
                        )
                    )
                    if cur.rowcount > 0: cur_order_id = order_id
            
            if cur_order_id <= 0:
                res['err'] = (-1, "Can't Create Order(%d)" % order_id)
                self.req.exitjs(res)
            res['order_id'] = cur_order_id
            
            if ord_comment:
                receipt_id = self.get_receipt_id(cur_order_id, ord_creation_date)
                cur.execute('insert into receipt_comment values (null,%s,1,%s,1,%s,%s)', (
                    receipt_id, now_ts, self.user_name, ord_comment
                    )
                )
            
            if order_close:
                try:
                    ord_info = {
                        'price_level': price_level,
                        'order_date': ord_order_date,
                        'creation_date': ord_creation_date,
                        'assoc_name': assoc[1],
                        'cashier_name': self.user_name,
                        'order_id': cur_order_id
                        }
                    self.create_virtual_receipt(cur, ord_info, ord_global, ord_items, False)
                
                    ar = self.modify_item(sur, items)
                    cur.execute("update sorder set ord_flag=ord_flag|%d,ord_items_js=%%s where ord_id=%d" % (
                        (ar == len(items) and self.OF_COMPLETED or 0),
                        cur_order_id,
                        ),
                        (
                        json.dumps(items, separators=(',',':')),
                        )
                    )
                except Exception, e:
                    res['err'] = (-1, 'Exception: ' + str(traceback.format_exc()))
            
        finally:
            try:
                dbc.close()
            except Exception:
                pass
        
        self.req.writejs(res)

    def modify_item(self, cur, items, minus=True):
        k = 0
        for item in items:
            if item.get('err'): continue
            cur.execute('update inventory set lastedit=now() where itemsid=? and itemno=? and datastate=0 and QtyStore1-CustOrdQty=AvailQty and CompanyOHQty=QtyStore1', (item['id'], item['num']))
            cur.execute('select @@rowcount')
            if cur.fetchall()[0][0] <= 0: continue
            cur.execute('select ReorderNotNull,CompanyOHQty,CustOrdQty,CmpMin,TotO_O,Cost,LastCost from inventory where itemsid=?', (item['id'],))
            ReorderNotNull,CompanyOHQty,CustOrdQty,CmpMin,TotO_O,Cost,LastCost = map(float, cur.fetchall()[0])
            item['prev_qty'] = (CompanyOHQty,CustOrdQty,CmpMin,TotO_O,Cost,LastCost)
            if minus:
                CompanyOHQty_new = CompanyOHQty - item['in_base_qty']
            else:
                CompanyOHQty_new = CompanyOHQty + item['in_base_qty']
            AvailQty_new = CompanyOHQty_new - CustOrdQty
            if ReorderNotNull:
                if AvailQty_new + TotO_O <= CmpMin:
                    BelowReorder_new = 1
                else:
                    BelowReorder_new = 0
                cur.execute('update inventory set BelowReorder=?,CompanyOHQty=?,QtyStore1=?,AvailQty=?,lastedit=now() where itemsid=?', (
                    BelowReorder_new,
                    CompanyOHQty_new,
                    CompanyOHQty_new,
                    AvailQty_new,
                    item['id'],
                    )
                )
            else:
                cur.execute('update inventory set CompanyOHQty=?,QtyStore1=?,AvailQty=?,lastedit=now() where itemsid=?', (
                    CompanyOHQty_new,
                    CompanyOHQty_new,
                    AvailQty_new,
                    item['id'],
                    )
                )
            cur.execute("insert into changejournal values(default,'Inventory',?,1,now(),'POSX', '-1')", (item['id'],))
            cur.execute('commit')
                
            k += 1

        return k
    
    def check_item(self, cur, price_level, items, jsr=None, no_price_check=False):
        ret = True
        k = -1
        for item in items:
            k += 1
            cur.execute('select unitofmeasure,price'+str(price_level+1)+' from inventory where itemsid=? and itemno=? and datastate=0 and QtyStore1-CustOrdQty=AvailQty and CompanyOHQty=QtyStore1',(
                item['id'],
                item['num'],
                )
            )
            r = cur.fetchall()
            if not r:
                err = 'Invalid'
                if jsr == None:
                    ret = False
                    item['err'] = err
                    continue
                else:
                    jsr['err'] = (k, err)
                    return False
        
            r = r[0]
            in_uom_idx = item['in_uom_idx']
            unit = item['units'][ in_uom_idx ]
            in_uom = unit[2].lower()
            in_price = unit[0][price_level]
            if in_uom_idx == 0:
                uom = (r[0] or '').lower()
                price = rex(float(r[1]), 2)
                if uom == in_uom:
                    if (no_price_check or price == 0.0 or price == in_price) and unit[3] == 1.00: continue
                    err = 'Not Matched - (Price:%0.2f, Factor:%0.2f) VS (Price:%0.2f, Factor:%0.2f)' % (
                        price, 1, in_price, unit[3]
                        )
                    if jsr == None:
                        ret = False
                        item['err'] = err
                        continue
                    else:
                        jsr['err'] = (k, err)
                        return False
                    
            if not in_uom:
                err = 'Empty UOM'
                if jsr == None:
                    ret = False
                    item['err'] = err
                    continue
                else:
                    jsr['err'] = (k, err)
                    return False
        
            cur.execute('select price'+str(price_level+1)+',unitfactor from InventoryUnits where itemsid=? and unitofmeasure=?', (item['id'], in_uom))
            r = cur.fetchall()
            if not r:
                err = 'UOM(%s) Not Found' % in_uom
                if jsr == None:
                    ret = False
                    item['err'] = err
                    continue
                else:
                    jsr['err'] = (k, err)
                    return False
            
            r = r[0]
            price = rex(float(r[0]), 2)
            factor = rex(float(r[1]), 2)
            if (no_price_check or price == 0.0 or price == in_price) and factor == unit[3]: continue
            err = 'Not Matched - (Price:%0.2f, Factor:%0.2f) VS (Price:%0.2f, Factor:%0.2f)' % (
                price, factor, in_price, unit[3]
                )
            if jsr == None:
                ret = False
                item['err'] = err
                continue
            else:
                jsr['err'] = (k, err)
                return False
    
        return ret
    
    def fn_reverse(self):
        rid = self.req.psv_int('rid')
        if not rid: return
        
        db = self.db()
        cur = db.cur()
        
        db_col_nzs = ('ord_id', 'ord_ref_id', 'ord_flag', 'ord_assoc_id', 'ord_user_id', 'ord_price_level', 'ord_order_date', 'ord_creation_date', 'ord_paid_date', 'ord_rev', 'ord_global_js', 'ord_items_js', 'ord_comment_js')
        cur.execute('select * from sorder where ord_id=%d and ord_flag&%d=%d' % (
            rid, self.OF_REVERSING|self.OF_REVERSED|self.OF_COMPLETED, self.OF_COMPLETED
            )
        )
        r = cur.fetchall()
        if not r: return
        r = dict(zip(db_col_nzs, r[0]))
        
        assoc_id = int(r['ord_assoc_id'])
        price_level = int(r['ord_price_level'])
        ord_global = json.loads(r['ord_global_js'])
        ord_global['memo'] = self.req.psv_ustr('reason')[:512].strip()
        ord_items = items = json.loads(r['ord_items_js'])
        for item in items:
            if item.has_key('prev_qty'): del item['prev_qty']
            if item.has_key('err'): del item['err']
        
        dbc = self.get_rdb()
        sur = dbc.cursor()
        res = {'order_id':0, 'err':None}
        ts = int(time.time())
        
        try:
            self.check_item(sur, price_level, items, None, True)
            cur.execute("update sorder set ord_flag=ord_flag|%d where ord_id=%d and ord_flag&%d=%d" % (
                self.OF_REVERSED,
                rid,
                self.OF_REVERSING|self.OF_REVERSED|self.OF_COMPLETED,
                self.OF_COMPLETED
                )
            )
            if cur.rowcount > 0:
                receipt_id = self.get_receipt_id(rid, r['ord_creation_date'])
                cur.execute("insert into receipt_comment values (null,%s,1,%s,1,%s,%s)", (
                    receipt_id, ts, self.user_name, 'Reversed'
                    )
                )
                cur.execute("insert into sorder values(null,%d,%d,%d,%d,%d,%d,%d,%d,0,%%s,%%s,'')" % (
                    rid,
                    self.OF_REVERSING | self.OF_CLOSE,
                    assoc_id,
                    self.user_id,
                    price_level,
                    ts,
                    ts,
                    0,
                    ),
                    (
                    json.dumps(ord_global, separators=(',',':')),
                    json.dumps(ord_items, separators=(',',':')),
                    )
                )
                ord_id = res['order_id'] = cur.lastrowid or 0
                cur.execute('update sorder set ord_ref_id=%d where ord_id=%d' % (ord_id, rid))
                
                assoc = self.finduser(assoc_id)
                ord_info = {
                    'price_level': price_level,
                    'order_date': ts,
                    'creation_date': ts,
                    'assoc_name': assoc and assoc[1] or '',
                    'cashier_name': self.user_name,
                    'order_id': ord_id,
                    'ord_ref': r
                }
                self.create_virtual_receipt(cur, ord_info, ord_global, ord_items, True)
            
                try:
                    ar = self.modify_item(sur, items, False)
                    cur.execute("update sorder set ord_flag=ord_flag|%d,ord_items_js=%%s where ord_id=%d" % (
                        ar == len(items) and self.OF_COMPLETED or 0,
                        ord_id
                        ),
                        (
                        json.dumps(items, separators=(',',':')),
                        )
                    )
                except Exception, e:
                    res['err'] = 'Exception: ' + str(traceback.format_exc())
            
        finally:
            try:
                dbc.close()
            except Exception:
                pass
            
        self.req.writejs(res)
    
    def fn_delete(self):
        rid = self.req.psv_int('rid')
        if not rid: return
    
        db = self.db()
        cur = db.cur()
        cur.execute('delete from sorder where ord_id=%d and ord_flag&%d=%d' % (
            rid, self.OF_CLOSE, 0
            )
        )
        
        if cur.rowcount <= 0: return
        self.req.writejs({'order_id':rid})
    
    def fn_mark(self):
        rid = self.req.psv_int('rid')
        if not rid: return
        
        is_paid = self.req.psv_int('is_paid')
        
        ts = int(time.time())
        
        db = self.db()
        cur = db.cur()
        
        if is_paid:
            ord_comment = 'Mark As Paid'
            cur.execute("update sorder set ord_flag=ord_flag|%d,ord_paid_date=%d where ord_id=%d and ord_flag&%d=%d" % (
                self.OF_PAID, ts,
                rid, self.OF_PAID|self.OF_REVERSING|self.OF_REVERSED|self.OF_PAYABLE, self.OF_PAYABLE
                )
            )
            
        else:
            ord_comment = 'Mark As UnPaid'
            cur.execute("update sorder set ord_flag=ord_flag&%d,ord_paid_date=0 where ord_id=%d and ord_flag&%d=%d" % (
                ~self.OF_PAID,
                rid, self.OF_PAID|self.OF_REVERSING|self.OF_REVERSED|self.OF_PAYABLE, self.OF_PAID|self.OF_PAYABLE
                )
            )
        if cur.rowcount <= 0: return
        
        cur.execute('select ord_creation_date from sorder where ord_id=%s', (rid,))
        rows = cur.fetchall()
        if rows:
            receipt_id = self.get_receipt_id(rid, rows[0][0])
            cur.execute("insert into receipt_comment values (null,%s,1,%s,1,%s,%s)", (
                receipt_id, ts, self.user_name, ord_comment
                )
            )
        
        self.req.writejs({'order_id':rid, 'is_paid':is_paid})
    
    
    def get_receipt_id(self, ord_id, creation_date):
        return ((ord_id & ((1 << 32) - 1)) << 32) | (creation_date & ((1 << 32) - 1))
    
    def fn_addcomment(self):
        rid = self.req.psv_int('rid')
        if not rid: return
        
        comment = self.req.psv_ustr('comment')[:256].strip()
        if not comment: return
        
        db = self.db()
        cur = db.cur()
        
        cur.execute('select ord_creation_date from sorder where ord_id=%s', (rid,))
        rows = cur.fetchall()
        if rows <= 0: return
        
        receipt_id = self.get_receipt_id(rid, rows[0][0])
        cur.execute('insert into receipt_comment values (null,%s,1,%s,0,%s,%s)', (
            receipt_id, int(time.time()), self.user_name, comment
            )
        )
        
        self.req.writejs({'order_id':rid})
        
    def fn_find(self):
        rid = self.qsv_int('rid')
        if not rid: return

        db = self.db()
        cur = db.cur()
        cur.execute('select count(*) from sorder where ord_id=%d' % (rid, ))
        self.req.writejs( { 'order_id': cur.fetchall()[0][0] and rid or 0 } )

    def fn_hist(self):
        d = {
            'USER_PERM_BIT': config.USER_PERM_BIT,
            'userlist': self.getuserlist(),
            'user_lvl': self.user_lvl,
            'user_id': self.user_id,
        }
        self.req.writefile('sorder_hist.html', d)

    def fn_print(self):
        rid = self.qsv_int('rid')
        if not rid: return
        
        db = self.db()
        cur = db.cur()
        
        db_col_nzs = ('ord_id', 'ord_ref_id', 'ord_flag', 'ord_assoc_id', 'ord_user_id', 'ord_price_level', 'ord_order_date', 'ord_creation_date', 'ord_paid_date', 'ord_rev', 'ord_global_js', 'ord_items_js', 'ord_comment_js', 'ord_assoc_name', 'ord_cashier_name')
        cur.execute('select i.*,a.user_name,c.user_name from sorder i left join user a on (i.ord_assoc_id=a.user_id) left join user c on (i.ord_user_id=c.user_id) where i.ord_id=%d' % (rid,))
        r = cur.fetchall()
        if not r: return
        r = dict(zip(db_col_nzs, r[0]))
        
        receipt_id = self.get_receipt_id(rid, r['ord_creation_date'])
        
        ord_items = r['ord_items'] = r['ord_items_js'] = json.loads(r['ord_items_js'])
        ord_global = r['ord_global'] = r['ord_global_js'] = json.loads(r['ord_global_js'])
        
        ord_flag = int(r['ord_flag'])
        r['ord_is_reversed'] = ord_flag & self.OF_REVERSED
        r['ord_is_reversing'] = ord_flag & self.OF_REVERSING
        r['ord_is_completed'] = ord_flag & self.OF_COMPLETED
        r['ord_is_paid'] = ord_flag & self.OF_PAID
        r['ord_is_payable'] = ord_flag & self.OF_PAYABLE
        r['ord_is_close'] = ord_flag & self.OF_CLOSE
        
        r['ord_order_date'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r['ord_order_date'])))
        r['ord_creation_date'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r['ord_creation_date'])))
        r['ord_paid_date'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r['ord_paid_date'])))
        r['auto_print'] = self.qsv_int('auto_print')
        
        r['price_lvls'] = self.PRICE_LEVELS
        
        comment = []
        for x in json.loads('[' + r['ord_comment_js'] + ']'):
            if not x: continue
            comment.append((
                time.strftime("%m/%d/%y %I:%M:%S %p", time.localtime(x[0])),
                x[1],
                x[2],
                x[3]
            ))
            
        cur.execute('select ts,name,flag,comment from receipt_comment where sid=%s and sid_type=1 order by rc_id asc', (receipt_id,))
        for x in cur.fetchall():
            comment.append((
                time.strftime("%m/%d/%y %I:%M:%S %p", time.localtime(x[0])),
                x[1],
                x[2],
                x[3]
            ))
            
        r['comment'] = r['ord_comment_js'] = comment
        
        cur.execute('select r.*,d.name,d.ts from deliveryv2_receipt r left join deliveryv2 d on (r.d_id=d.d_id) where r.num=%s order by r.d_id desc', (r['ord_id'],))
        nzs = cur.column_names
        r['delivery_info'] = delivery_info = []
        for x in cur.fetchall():
            x = dict(zip(nzs, x))
            x['ts'] = time.strftime("%m/%d/%y", time.localtime(x['ts']))
            x['js'] = json.loads(x['js'])
            delivery_info.append(x)
        r['users_lku'] = dict([ x[:2] for x in self.getuserlist() ])
        r['PROBLEMS'] = Delivery.PROBLEMS
        
        self.req.writefile('sorder_print_v2.html', r)

    def fn_getpage(self):
        uid = self.qsv_int('uid')
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        
        if pgsz > 100 or eidx - sidx > 5: return
        
        db = self.db()
        cur = db.cur()
        
        rpg = {}
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select i.ord_id,i.ord_flag,i.ord_assoc_id,i.ord_order_date,i.ord_creation_date,i.ord_global_js,u.user_name from sorder i left join user u on (i.ord_assoc_id=u.user_id)%s order by i.ord_id desc limit %s,%s' % (
                uid and ' where i.ord_assoc_id=%d' % (uid,) or '',
                sidx * pgsz, (eidx - sidx) * pgsz
                )
            )
            d = cur.fetchall()
            
            for i in range(sidx, eidx): rpg[i] = []
            if d:
                k = 0
                for r in d:
                    flag = int(r[1])
                    if flag & self.OF_REVERSING:
                        r_type = 'Reversing'
                    elif flag & self.OF_REVERSED:
                        r_type = 'Reversed'
                    else:
                        r_type = 'Regular'
                        
                    if not (flag & (self.OF_REVERSING | self.OF_REVERSED)) and (flag & self.OF_PAYABLE):
                        if flag & self.OF_PAID:
                            paid_s = 'Y'
                        else:
                            paid_s = ''
                    else:
                        paid_s = '-'
                        
                    if flag & self.OF_CLOSE:
                        r_status = 'Close'
                        if not flag & self.OF_COMPLETED:
                            r_type = '***' + r_type
                    else:
                        r_status = 'Open'
                        
                    ord_global = json.loads(r[5])
                    r = (
                        r[0],
                        r_status,
                        r_type,
                        r[6] or '',
                        "$%0.2f" % ord_global['total'],
                        paid_s,
                        ord_global['memo'].split('\n', 2)[0].strip(),
                        time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r[3]))),
                        time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(int(r[4]))),
                    )
                    rpg[sidx].append(r)
                    k += 1
                    if k == pgsz:
                        sidx += 1
                        k = 0
        
        cur.execute('select count(*) from sorder' + (uid and ' where ord_assoc_id=%d' % (uid,) or ''))
        rlen = int(cur.fetchall()[0][0])
        
        self.req.writejs( {'res':{'len':rlen, 'rpg':rpg}} )

    def create_virtual_receipt(self, cur, ord_info, ord_global, ord_items, reverse=False):
        ord_id = ord_info['order_id']
        #doc_sid = ((ord_id & ((1 << 32) - 1)) << 32) | (ord_info['creation_date'] & ((1 << 32) - 1))
        doc_sid = self.get_receipt_id(ord_id, ord_info['creation_date'])
        if reverse:
            doc_flag = (1 << 8) | 2
            ord_ref = ord_info['ord_ref']
            #ref_ord_id = ((int(ord_ref['ord_id']) & ((1 << 32) - 1)) << 32) | (int(ord_ref['ord_creation_date']) & ((1 << 32) - 1))
            ref_ord_id = self.get_receipt_id(int(ord_ref['ord_id']), int(ord_ref['ord_creation_date']))
            cur.execute('update sync_receipts set type=type|1 where sid=%d and sid_type=1' % (ref_ord_id,))
            #skip item history
            #db.query('update sync_items_hist set flag=flag|1 where docsid=%d and sid_type=1' % (ref_ord_id,))
        else:
            doc_flag = 0
            
        sql = "replace into sync_receipts values (%d,1,null,%s,null,0,%d,%d,%%s,%%s,%d,%d,%d,%%s,'[]')" % (
            doc_sid,
            ord_global['customer'] == None and 'null' or "'%s'" % ord_global['customer']['sid'],
            doc_flag,
            ord_id,
            ord_info['price_level'],
            ord_info['order_date'],
            ord_info['creation_date'],
        )
        cur.execute(sql, (
            ord_info['assoc_name'],
            ord_info['cashier_name'],
            json.dumps(ord_global, separators=(',',':')),
        ))
        
        items = {}
        for item in ord_items:
            v = items.setdefault(item['id'], [None, 0])
            v[0] = item
            v[1] += item['in_base_qty']
            
        vs = []
        for item_sid,item in items.items():
            item = item[0]
            lookup = set()
            lookup.add(unicode(item['num']))
            for unit in item['units']:
                if unit[1]: lookup.add(unit[1].strip().lower())
            for vend in item['vends']:
                if vend[1]: lookup.add(vend[1].strip().lower())
            for udf in item['udfs']:
                if udf[1]: lookup.add(udf[1].strip().lower())
            lookup.discard(u'')
            
            vs.append((
                item_sid,
                item['num'],
                u' '.join(lookup),
                item['in_desc'] or '',
                json.dumps({'alu': item['units'][0][1]}, separators=(',',':')),
            ))
            
        if vs: cur.executemany('replace into sync_receipts_items values (%s,%s,%s,%s,%s)', vs)
        
        vs = []
        k = 0
        for item_sid,item in items.items():
            base_qty = item[1]
            item = item[0]
            hist_sid = ((ord_id & ((1 << 32) - 1)) << 32) | k
            k += 1
            
            if not reverse: base_qty = -base_qty
            
            vs.append((
                hist_sid,
                item_sid,
                doc_sid,
                ord_id,
                doc_flag,
                ord_global['customer'] and ord_global['customer']['name'] or '',
                0,
                base_qty,
                0,
                0,
                0,
                ord_info['creation_date'],
            ))
            
        if vs: cur.executemany('replace into sync_items_hist values (%s,1,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', vs)
        
        cust = ord_global['customer']
        if cust:
            lookup = set()
            if cust['address1']: lookup.add(cust['address1'].strip().lower())
            if cust['phone1']: lookup.add( phonenum_parser.parse_phone_num(cust['phone1']) )
            lookup.discard(u'')
            
            customer_info = {
                'company': cust['company'] or '',
                'name': cust['lname'] or '',
                'addr1': cust['address1'] or '',
                'addr2': cust['address2'] or '',
                'city': cust['city'] or '',
                'state': cust['state'] or '',
                'zip': cust['zip'] or '',
                'phone': cust['phone1'] or ''
            }
            
            cur.execute("replace into sync_receipts_customers values (%s,%s,%s,%s)", (
                int(cust['sid']),
                cust['name'],
                u' '.join(lookup),
                json.dumps(customer_info, separators=(',',':')),
            ))
            
    def fn_load(self):
        rid = self.req.psv_int('rid')
        if not rid: return
        
        db = self.db()
        cur = db.cur()
        
        db_col_nzs = ('ord_id', 'ord_ref_id', 'ord_flag', 'ord_assoc_id', 'ord_user_id', 'ord_price_level', 'ord_order_date', 'ord_creation_date', 'ord_paid_date', 'ord_rev', 'ord_global_js', 'ord_items_js')
        cur.execute('select * from sorder where ord_id=%d' % (rid,))
        
        r = cur.fetchall()
        if not r: self.req.exitjs({'err': 'No Such Order'})
        r = dict(zip(db_col_nzs, r[0]))
        
        js = {}
        js['order_id'] = int(r['ord_id'])
        js['is_close'] = int(r['ord_flag']) & self.OF_CLOSE
        js['assoc_id'] = int(r['ord_assoc_id'])
        price_level = js['price_level'] = int(r['ord_price_level'])
        ord_order_date = int(r['ord_order_date'])
        ord_creation_date = int(r['ord_creation_date'])
        js['order_date'] = int(r['ord_order_date'])
        
        ord_global = js['global'] = json.loads(r['ord_global_js'])
        ord_items = js['items'] = json.loads(r['ord_items_js'])
        
        ids = set([str(x['id']) for x in ord_items])
        if not ids: self.req.exitjs({'err': 'No Items'})
        
        cur.execute('select sid,num,detail from sync_items where sid in (%s)' % (','.join(ids),))
        db_items = {}
        for r in cur.fetchall():
            db_items[ int(r[0]) ] = item_js = json.loads(r[2])
            item_js['num'] = int(r[1])
        
        errs = []
        if ord_global['customer']:
            cust = ord_global['customer']
            cur.execute("select sid,name,detail from sync_customers where sid=%s" % (cust['sid'],))
            res = cur.fetchall()
            if not res:
                errs.append('customer(%s) no longer valid' % cust['name'])
            else:
                res = res[0]
                cp_cust = json.loads(res[2])
                cp_cust['sid'] = str(res[0])
                cp_cust['name'] = res[1]
                ord_global['customer'] = cp_cust
        
        row_idx = 0
        for item in ord_items:
            row_idx += 1
            sid = item['id']
            num = item['num']
            item['id'] = str(sid)
            item['num'] = str(num)
            
            if item.has_key('in_base_qty'): del item['in_base_qty']
            if item.has_key('err'): del item['err']
            if item.has_key('prev_qty'): del item['prev_qty']
            
            db_item = db_items.get(sid)
            if not db_item:
                errs.append('Row %d - %d - no longer valid' % (row_idx, num))
                continue
            
            db_units = db_item['units']
            cp_units = [ [u[0][:],] + list(u[1:]) for u in db_units ]
            in_uom_idx = item['in_uom_idx']
            units = item['units']
            unit = units[in_uom_idx]
            uom = unit[2].lower()
            k = 0
            for u in cp_units:
                if u[2].lower() == uom: break
                k += 1
            if k == len(cp_units):
                errs.append('Row %d - %d - uom(%s) not found' % (row_idx, num, uom))
                continue
            cp_unit = cp_units[k]
            if cp_unit[3] != unit[3]:
                errs.append('Row %d - %d - %s - factor(%0.2f, %0.2f) not matched' % (row_idx, num, uom, unit[3], cp_unit[3]))
                continue
            
            if not cp_unit[0][ price_level ] and unit[0][ price_level ]:
                cp_unit[0][ price_level ] = unit[0][ price_level ]

            item['units'] = cp_units
            item['default_uom_idx'] = item['in_uom_idx'] = k
            item['udfs'] = db_item['udfs'][:]
            item['vends'] = db_item['vends'][:]
        
        js['err'] = '\n'.join(errs)
        self.req.writejs(js)

