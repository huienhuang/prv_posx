from sync_helper import *
import sys
import json
import time

def sync_purchaseorders(cj_data, mode=0):
    cur,sur = pos_db()
    mdb = sys_db()
    
    if mode:
        if mode == 1:
            mdb.query('delete from sync_purchaseorders')
            mdb.query('delete from sync_link_item where doc_type=1')
        where_sql = ''
    else:
        sids = [ str(x[1]) for x in cj_data if x[0] and x[0].lower() == 'purchaseorder' ]
        if not sids: return 0
        where_sql = ' where sid in (%s)' % (','.join(sids),)

    po = {}

    seq = 0
    sql = ''
    cur.execute("select sid,datastate,suppvendsid,suppvendcompany,ponum,clerk,status,comments,total,subtotal,discamount,discpercent,feeamount,termsdiscdays,termsnetdays,termsdisc,podate,poshipdate,pototduedate,pocanceldate,creationdate from PurchaseOrder" + where_sql + ' order by sid asc')
    cur_nzs = [ d[0].lower() for d in cur.description ]
    for r in cur.rows():
        r = dict(zip(cur_nzs, r))
        
        sid = r['sid']
        
        items = []
        sur.execute('select i.itemsid,i.sorefsid,i.sonum,d.deptsid,d.vendsid,i.nunits,i.qty,i.qtyrcvd,i.price,i.cost,i.discamount as discamt,i.discpercent as disc,i.unitofmeasure as uom,d.desc1,ifnull(ld.desc2,d.desc2,ld.desc2) as desc2,d.itemno,d.alu,d.upc from PurchaseOrderItem i left join PurchaseOrderItemDesc d on (i.sid=d.sid and i.itempos=d.itempos) left join PurchaseOrderItemLongDesc ld on (i.sid=ld.sid and i.itempos=ld.itempos) where i.sid=? order by i.itempos asc', (sid,))
        sur_nzs = [ d[0].lower() for d in sur.description ]
        item_sids = {}
        qty_count = rcvd_count = 0
        for rr in sur.rows():
            rr = dict(zip(sur_nzs, rr))
            item_sid = rr['itemsid']
            rr['nunits'] = round(float(rr['nunits']),5)
            rcvd = rr['qtyrcvd'] = round(float(rr['qtyrcvd']),5)
            qty = rr['qty'] = round(float(rr['qty']),5)
            rr['price'] = round(float(rr['price']),5)
            rr['cost'] = round(float(rr['cost']),5)
            rr['discamt'] = round(float(rr['discamt']),5)
            rr['disc'] = round(float(rr['disc']),5)
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
            rcvd_count += abs(rcvd)
            qty_stat = item_sids.setdefault(item_sid, [0, 0])
            qty_stat[0] += qty * rr['nunits']
            qty_stat[1] += rcvd * rr['nunits']
        
        r['suppvendcompany'] = r['suppvendcompany'] or ''
        global_js = json.dumps({
            'total': round(float(r['total']), 5),
            'subtotal': round(float(r['subtotal']), 5),
            'discamt': round(float(r['discamount']), 5),
            'discprc': round(float(r['discpercent']), 5),
            'feeamt': round(float(r['feeamount']), 5),
            'vend': r['suppvendcompany'],
            'itemcount': len(item_sids),
            'qtycount': qty_count,
            'rcvdcount': rcvd_count,
            'memo': r['comments'] or '',
            'termsdiscdays': r['termsdiscdays'],
            'termsnetdays': r['termsnetdays'],
            'termsdisc': round(float(r['termsdisc']), 5),
            'canceldate': r['pocanceldate'] and int(time.mktime(time.strptime(r['pocanceldate'], '%Y-%m-%d'))) or 0,
        }, separators=(',',':'))
        
        if mode != 1: mdb.query('delete from sync_link_item where doc_sid=%d and doc_type=1' % (sid,))
        status = (r['datastate'] << 16) | r['status']
        po[sid] = (r['suppvendcompany'], item_sids, status)
        
        seq += 1
        sqlt = "(%d,%d,%d,'%s','%s',%d,%d,%d,%d,'%s','%s')," % (
            sid,
            r['suppvendsid'],
            status,
            mdb.escape_string(r['ponum'] and r['ponum'].encode('utf8') or ''),
            mdb.escape_string(r['clerk'] and r['clerk'].encode('utf8') or ''),
            r['podate'] and int(time.mktime(time.strptime(r['podate'], '%Y-%m-%d'))) or 0,
            r['poshipdate'] and int(time.mktime(time.strptime(r['poshipdate'], '%Y-%m-%d'))) or 0,
            r['pototduedate'] and int(time.mktime(time.strptime(r['pototduedate'], '%Y-%m-%d'))) or 0,
            int(time.mktime(time.strptime(r['creationdate'].split('.')[0], '%Y-%m-%d %H:%M:%S'))),
            mdb.escape_string( global_js ),
            mdb.escape_string( json.dumps(items, separators=(',',':')) )
        )
        
        if len(sql) + len(sqlt) >= 1024 * (1024 - 1):
            print seq
            sql = 'replace into sync_purchaseorders values ' + sql[:-1]
            mdb.query(sql)
            sql = ''
        sql += sqlt
    
    if sql:
        sql = 'replace into sync_purchaseorders values ' + sql[:-1]
        mdb.query(sql)
        sql = ''
    
    #if seq:
    #    if mode:
    #        mdb.query('optimize table sync_purchaseorders')
    #        mdb.use_result()
    
    for xk, xv in po.items():
        for yk, yv in xv[1].items():
            sqlt = "(%d,%d,1,%d,%d,%d,'%s')," % (
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

    
    print 'sync_purchaseorders: R(%d)' % (seq, )
    return seq


g_sync_cb = ('purchaseorders', sync_purchaseorders)

if __name__ == '__main__':
    #sync_receipts( (('receipt', -6172729321342464255),) )
    sync_main(g_sync_cb)


