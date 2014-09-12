from sync_helper import *
import sys
import json
import time
import data_helper


def index_customers(customers):
    cur,sur = pos_db()
    mdb = sys_db()

    sql = ''
    for k, v in customers.items():
        name = v['company'] or v['name'] or u''
        
        lookup = set()
        if v['addr1']: lookup.add(v['addr1'].strip().lower())
        if v['phone']: lookup.add( data_helper.parse_phone_num(v['phone']) )
        lookup.discard(u'')
        
        sqlt = "(%d,'%s','%s','%s')," % (
            k,
            mdb.escape_string( name.encode('utf8') ),
            mdb.escape_string( u' '.join(lookup).encode('utf8') ),
            mdb.escape_string( json.dumps(v, separators=(',',':')) ),
        )
        
        if len(sql) + len(sqlt) >= 1024 * (1024 - 1):
            sql = 'replace into sync_receipts_customers values ' + sql[:-1]
            mdb.query(sql)
            sql = ''
        sql += sqlt
        
    if sql:
        sql = 'replace into sync_receipts_customers values ' + sql[:-1]
        mdb.query(sql)
        sql = ''
        
def index_items(items):
    cur,sur = pos_db()
    mdb = sys_db()

    sql = ''
    for k, v in items.items():
        lookup = set()
        lookup.add(unicode(v[0]))
        if v[1]: lookup.add(v[1].strip().lower())
        
        sur.execute('select udf1,udf2 from inventory where itemsid=?', (k,))
        r = sur.fetchall()
        if r:
            r = r[0]
            if r[0]: lookup.add(r[0].strip().lower())
            if r[1]: lookup.add(r[1].strip().lower())
        sur.execute('select alu from inventoryvendor where itemsid=? and alu is not null', (k,))
        for r in sur.fetchall(): lookup.add(r[0].strip().lower())
        sur.execute('select alu from InventoryUnits where itemsid=? and alu is not null', (k,))
        for r in sur.fetchall(): lookup.add(r[0].strip().lower())
        
        lookup.discard(u'')
        js = {'alu': v[1] or ''}
        sqlt = "(%d,%d,'%s','%s','%s')," % (
            k,
            v[0],
            mdb.escape_string( u' '.join(lookup).encode('utf8') ),
            mdb.escape_string( (v[2] or u'').encode('utf8') ),
            mdb.escape_string( json.dumps(js, separators=(',',':')) ),
        )
        
        if len(sql) + len(sqlt) >= 1024 * (1024 - 1):
            sql = 'replace into sync_receipts_items values ' + sql[:-1]
            mdb.query(sql)
            sql = ''
        sql += sqlt
        
    if sql:
        sql = 'replace into sync_receipts_items values ' + sql[:-1]
        mdb.query(sql)
        sql = ''

def sync_receipts(cj_data, mode=0):
    cur,sur = pos_db()
    mdb = sys_db()
    
    feed = []
    
    if mode:
        if mode == 1:
            mdb.query('delete from sync_receipts where sid_type=0')
            mdb.query('delete from sync_receipts_items')
            mdb.query('delete from sync_receipts_customers')
        where_sql = 'datastate=0'
    else:
        sids = [ str(x[1]) for x in cj_data if x[0] and x[0].lower() == 'receipt' ]
        if not sids: return 0
        where_sql = 'datastate=0 and sid in (%s)' % (','.join(sids),)

    idx_customers = {}
    idx_items = {}

    seq = 0
    sql = ''
    cur.execute("select sid,billtosid,receiptnum,receipttype,receiptstatus,receiptrefsid,sorefsid,sotype,sonum,tendertype,cashier,clerk,total,subtotal,taxamount,discamount,discpercent,receiptdate,receipttime,feeamount,creationdate,comments,pricelevel,comments,workstation from Receipt where " + where_sql + ' order by sid asc')
    cur_nzs = [ d[0].lower() for d in cur.description ]
    for r in cur.rows():
        r = dict(zip(cur_nzs, r))
        
        sid = r['sid']
        feed.append( (sid, 0) )
        
        customer_info = None
        if r['billtosid'] != None:
            sur.execute("select first custcompany,custlname,custaddress1,custaddress2,custcity,custstate,custzip,custphone1 from receiptcustomer where sid=?", (sid,))
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
                customer_info['loc'] = data_helper.get_location_hash(c[2], c[4], c[5], c[6])
                idx_customers[ r['billtosid'] ] = customer_info
        
        shipping_info = None
        sur.execute("select shipcompany,shipfullname,shipaddress,shipaddress2,shipcity,shipstate,shipzip,shipphone1,shipprovider,trackingnumber,shipamount,shiptaxamount,shipdate from receiptshipto where sid=?", (sid,))
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
                'tracking': s[9] or '',
                'amt': round(float(s[10]),5),
                'taxamt': round(float(s[11]),5),
                'date': s[12] and int(time.mktime(time.strptime(s[12].split('.')[0], '%Y-%m-%d %H:%M:%S'))) or 0,
            }
            if not any(shipping_info.values()):
                shipping_info = None
            else:
                shipping_info['loc'] = data_helper.get_location_hash(s[2], s[4], s[5], s[6])
        
        items = []
        sur.execute('select i.itemsid,i.docrefsid,d.deptsid,d.vendsid,i.clerk,i.serialnum as snum,i.nunits,i.qty,i.origprice,i.price,i.pricetax,i.cost,i.discountpercent as disc,i.discountsource as discsrc,i.unitofmeasure as uom,d.desc1,ifnull(ld.desc2,d.desc2,ld.desc2) as desc2,d.itemno,d.alu,d.upc from ReceiptItem i left join ReceiptItemDesc d on (i.sid=d.sid and i.itempos=d.itempos) left join ReceiptItemLongDesc ld on (i.sid=ld.sid and i.itempos=ld.itempos) where i.sid=? order by i.itempos asc', (sid,))
        sur_nzs = [ d[0].lower() for d in sur.description ]
        item_sids = {}
        qty_count = 0
        for rr in sur.rows():
            rr = dict(zip(sur_nzs, rr))
            item_sid = rr['itemsid']
            rr['nunits'] = round(float(rr['nunits']),5)
            qty = rr['qty'] = round(float(rr['qty']),5)
            rr['origprice'] = round(float(rr['origprice']),5)
            rr['price'] = round(float(rr['price']),5)
            rr['pricetax'] = round(float(rr['pricetax']),5)
            rr['cost'] = round(float(rr['cost']),5)
            rr['disc'] = round(float(rr['disc']),5)
            rr['uom'] = rr['uom'] or ''
            rr['snum'] = rr['snum'] or ''
            rr['alu'] = rr['alu'] or ''
            rr['upc'] = rr['upc'] or 0
            if rr['desc2']:
                desc1 = rr['desc1'] and rr['desc1'].strip() or ''
                desc2 = rr['desc2'].strip()
                if desc2[-3:] == '...': desc2 = desc2[:-3]
                if len(desc2) > len(desc1): rr['desc1'] = desc2
            del rr['desc2']
            idx_items[ item_sid ] = (rr['itemno'], rr['alu'], rr['desc1'])
            items.append(rr)
            
            if item_sid != 1000000005:
                qty_count += abs(qty)
                item_sids[item_sid] = False
            
        sur.execute('select TenderType, sum(TenderAmount), list(tendernumber) from ReceiptTender where SID = ? group by TenderType', (sid,))
        tender = [ { 'type': d[0], 'amount': round(float(d[1]), 5), 'numlst': d[2] } for d in sur.fetchall() ]
        #['', 'cash', 'check', 'visa', 'debit', 'P5', 'account', 'P7', 'deposit', 'split']
        
        gjs = {
            'total': round(float(r['total']), 5),
            'subtotal': round(float(r['subtotal']), 5),
            'discamt': round(float(r['discamount']), 5),
            'discprc': round(float(r['discpercent']), 5),
            'taxamt': round(float(r['taxamount']), 5),
            'feeamt': round(float(r['feeamount']), 5),
            'tendertype': r['tendertype'],
            'sonum': r['sonum'],
            'customer': customer_info,
            'shipping': shipping_info,
            'tender': tender,
            'itemcount': len(item_sids),
            'qtycount': qty_count,
            'memo': r['comments'] or '',
            'station': r['workstation'],
        }
        gjs['crc'] = data_helper.get_receipt_crc(r, gjs, items)
        gjs['items_crc'] = data_helper.get_doc_items_crc(items)
        global_js = json.dumps(gjs, separators=(',',':'))
        
        seq += 1
        sqlt = "(%d,0,%s,%s,%s,%d,%d,%d,'%s','%s',%d,%d,%d,'%s','%s')," % (
            sid,
            r['receiptrefsid'] == None and 'null' or "'%s'" % r['receiptrefsid'],
            r['billtosid'] == None and 'null' or "'%s'" % r['billtosid'],
            r['sorefsid'] == None and 'null' or "'%s'" % r['sorefsid'],
            r['sotype'],
            (r['tendertype'] << 16) | (r['receipttype'] << 8) | r['receiptstatus'],
            r['receiptnum'],
            mdb.escape_string(r['clerk'] and r['clerk'].encode('utf8') or ''),
            mdb.escape_string(r['cashier'] and r['cashier'].encode('utf8') or ''),
            r['pricelevel'],
            int(time.mktime(time.strptime(r['receiptdate'] + ' ' + r['receipttime'].split('.')[0], '%Y-%m-%d %H:%M:%S'))),
            int(time.mktime(time.strptime(r['creationdate'].split('.')[0], '%Y-%m-%d %H:%M:%S'))),
            mdb.escape_string( global_js ),
            mdb.escape_string( json.dumps(items, separators=(',',':')) )
        )
        
        if len(sql) + len(sqlt) >= 1024 * (1024 - 1):
            print seq
            sql = 'replace into sync_receipts values ' + sql[:-1]
            mdb.query(sql)
            sql = ''
        sql += sqlt
    
    if sql:
        sql = 'replace into sync_receipts values ' + sql[:-1]
        mdb.query(sql)
        sql = ''
    
    #if seq:
    #    if mode:
    #        mdb.query('optimize table sync_receipts')
    #        mdb.use_result()
    
    index_customers(idx_customers)
    index_items(idx_items)
    
    
    while feed:
        qjs = mdb.escape_string( json.dumps(feed[:1000], separators=(',',':')) )
        mdb.query("insert into sync_chg values (null,2,'%s')" % (
            qjs,
            )
        )
        feed = feed[1000:]
        
    
    print 'sync_receipts: R(%d)' % (seq, )
    return seq


g_sync_cb = ('receipts', sync_receipts)

if __name__ == '__main__':
    #sync_receipts( (('receipt', -6172729321342464255),) )
    sync_main(g_sync_cb)


