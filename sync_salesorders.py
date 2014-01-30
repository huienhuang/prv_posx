from sync_helper import *
import sys
import json
import time

def sync_salesorders(cj_data, mode=0):
    cur,sur = pos_db()
    mdb = sys_db()
    
    if mode:
        if mode == 1:
            mdb.query('delete from sync_salesorders')
            mdb.query('delete from sync_link_item where doc_type=2')
        where_sql = ''
    else:
        sids = [ str(x[1]) for x in cj_data if x[0] and x[0].lower() == 'salesorder' ]
        if not sids: return 0
        where_sql = ' where sid in (%s)' % (','.join(sids),)

    so = {}

    seq = 0
    sql = ''
    cur.execute("select sid,datastate,sonum,sotype,status,billtosid,comments,cashier,clerk,pricelevel,total,sodue,subtotal,taxamount,discamount,discpercent,feeamount,shipamount,deposittaken,depositused,shippingused,sodate,soduedate,creationdate from SalesOrder" + where_sql + ' order by sid asc')
    cur_nzs = [ d[0].lower() for d in cur.description ]
    for r in cur.rows():
        r = dict(zip(cur_nzs, r))
        
        sid = r['sid']
        
        customer_info = None
        if r['billtosid'] != None:
            sur.execute("select first custcompany,custlname,custaddress1,custaddress2,custcity,custstate,custzip,custphone1 from SalesOrderCustomer where sid=?", (sid,))
            c = sur.fetchall()
            if c:
                c = c[0]
                customer_info = {
                    'company': c[0] or '',
                    'name': c[1] or '',
                    'addr1': c[2] or '',
                    'addr2': c[3] or '',
                    'city': c[4] or '',
                    'state': c[5] or '',
                    'zip': c[6] or '',
                    'phone': c[7] or ''
                }
        
        shipping_info = None
        sur.execute("select shipcompany,shipfullname,shipaddress,shipaddress2,shipcity,shipstate,shipzip,shipphone1,shipprovider,shipamount,shiptaxamount from SalesOrderShipTo where sid=?", (sid,))
        s = sur.fetchall()
        if s:
            s = s[0]
            shipping_info = {
                'company': s[0] or '',
                'name': s[1] or '',
                'addr1': s[2] or '',
                'addr2': s[3] or '',
                'city': s[4] or '',
                'state': s[5] or '',
                'zip': s[6] or '',
                'phone': s[7] or '',
                'provider': s[8] or '',
                'amt': round(float(s[9]),5),
                'taxamt': round(float(s[10]),5),
            }
            if not any(shipping_info.values()): shipping_info = None
        
        items = []
        sur.execute('select i.itemsid,d.deptsid,d.vendsid,i.clerk,i.serialnum as snum,i.nunits,i.qty,i.qtysent,i.origprice,i.price,i.pricetax,i.cost,i.discountpercent as disc,i.discountsource as discsrc,i.unitofmeasure as uom,d.desc1,ifnull(ld.desc2,d.desc2,ld.desc2) as desc2,d.itemno,d.alu,d.upc from SalesOrderItem i left join SalesOrderItemDesc d on (i.sid=d.sid and i.itempos=d.itempos) left join SalesOrderItemLongDesc ld on (i.sid=ld.sid and i.itempos=ld.itempos) where i.sid=? order by i.itempos asc', (sid,))
        sur_nzs = [ d[0].lower() for d in sur.description ]
        item_sids = {}
        qty_count = sent_count = 0
        for rr in sur.rows():
            rr = dict(zip(sur_nzs, rr))
            item_sid = rr['itemsid']
            rr['nunits'] = round(float(rr['nunits']),5)
            sent = rr['qtysent'] = round(float(rr['qtysent']),5)
            qty = rr['qty'] = round(float(rr['qty']),5)
            rr['price'] = round(float(rr['price']),5)
            rr['pricetax'] = round(float(rr['pricetax']),5)
            rr['origprice'] = round(float(rr['origprice']),5)
            rr['cost'] = round(float(rr['cost']),5)
            rr['disc'] = round(float(rr['disc']),5)
            rr['snum'] = rr['snum'] or ''
            rr['uom'] = rr['uom'] or ''
            rr['alu'] = rr['alu'] or ''
            rr['upc'] = rr['upc'] or 0
            if rr['desc2']:
                desc1 = rr['desc1'] and rr['desc1'].strip() or ''
                desc2 = rr['desc2'].strip()
                if desc2[-3:] == '...': desc2 = desc2[:-3]
                if len(desc2) > len(desc1): rr['desc1'] = desc2
            del rr['desc2']
            items.append(rr)
            
            qty_count += abs(qty)
            sent_count += abs(sent)
            qty_stat = item_sids.setdefault(item_sid, [0, 0])
            qty_stat[0] += qty * rr['nunits']
            qty_stat[1] += sent * rr['nunits']
        
        global_js = json.dumps({
            'total': round(float(r['total']), 5),
            'subtotal': round(float(r['subtotal']), 5),
            'discamt': round(float(r['discamount']), 5),
            'discprc': round(float(r['discpercent']), 5),
            'feeamt': round(float(r['feeamount']), 5),
            'taxamt': round(float(r['taxamount']), 5),
            'shipamt': r['shipamount'] and round(float(r['shipamount']), 5) or 0,
            'itemcount': len(item_sids),
            'qtycount': qty_count,
            'sentcount': sent_count,
            'memo': r['comments'] or '',
            'customer': customer_info,
            'shipping': shipping_info,
            'deposittaken': round(float(r['deposittaken']), 5),
            'depositused': round(float(r['depositused']), 5),
            'shippingused': round(float(r['shippingused']), 5),
            'due': round(float(r['sodue']), 5),
        }, separators=(',',':'))
        
        if mode != 1: mdb.query('delete from sync_link_item where doc_sid=%d and doc_type=2' % (sid,))
        status = (r['datastate'] << 16) | (r['sotype'] << 4) | r['status']
        so[sid] = (customer_info['company'] or customer_info['name'] or '', item_sids, status)
        
        seq += 1
        sqlt = "(%d,%d,%d,%d,'%s','%s','%s',%d,%d,%d,'%s','%s')," % (
            sid,
            r['billtosid'],
            status,
            r['pricelevel'],
            mdb.escape_string(r['sonum'] and r['sonum'].encode('utf8') or ''),
            mdb.escape_string(r['clerk'] and r['clerk'].encode('utf8') or ''),
            mdb.escape_string(r['cashier'] and r['cashier'].encode('utf8') or ''),
            r['sodate'] and int(time.mktime(time.strptime(r['sodate'], '%Y-%m-%d'))) + 11 * 3600 or 0,
            r['soduedate'] and int(time.mktime(time.strptime(r['soduedate'], '%Y-%m-%d'))) + 11 * 3600 or 0,
            int(time.mktime(time.strptime(r['creationdate'].split('.')[0], '%Y-%m-%d %H:%M:%S'))),
            mdb.escape_string( global_js ),
            mdb.escape_string( json.dumps(items, separators=(',',':')) )
        )
        
        if len(sql) + len(sqlt) >= 1024 * (1024 - 1):
            print seq
            sql = 'replace into sync_salesorders values ' + sql[:-1]
            mdb.query(sql)
            sql = ''
        sql += sqlt
    
    if sql:
        sql = 'replace into sync_salesorders values ' + sql[:-1]
        mdb.query(sql)
        sql = ''
    
    #if seq:
    #    if mode:
    #        mdb.query('optimize table sync_salesorders')
    #        mdb.use_result()
    
    for xk, xv in so.items():
        for yk, yv in xv[1].items():
            sqlt = "(%d,%d,2,%d,%d,%d,'%s')," % (
                yk, xk, xv[2] | (int(yv[0] == yv[1]) << 8), int(yv[0]), int(yv[1]),
                mdb.escape_string(xv[0].encode('utf8'))
            )
            if len(sql) + len(sqlt) >= 1024 * (1024 - 1):
                print seq
                sql = 'replace into sync_link_item values ' + sql[:-1]
                mdb.query(sql)
                sql = ''
            sql += sqlt
    
    if sql:
        sql = 'replace into sync_link_item values ' + sql[:-1]
        mdb.query(sql)
        sql = ''

    
    print 'sync_salesorders: R(%d)' % (seq, )
    return seq


g_sync_cb = ('salesorders', sync_salesorders)

if __name__ == '__main__':
    #sync_receipts( (('receipt', -6172729321342464255),) )
    sync_main(g_sync_cb)


