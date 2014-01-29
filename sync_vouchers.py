from sync_helper import *
import sys
import json
import time

def sync_vouchers(cj_data, mode=0):
    cur,sur = pos_db()
    mdb = sys_db()
    
    if mode:
        if mode == 1: mdb.query('delete from sync_vouchers')
        where_sql = ''
    else:
        sids = [ str(x[1]) for x in cj_data if x[0] and x[0].lower() == 'voucher' ]
        if not sids: return 0
        where_sql = ' where sid in (%s)' % (','.join(sids),)

    rep_seq = del_seq = 0
    sql = ''
    cur.execute("select sid,datastate,vouchertype,voucherstatus,vouchernum,docrefsid,ponum,clerk,invoicenumber,comments,suppvendsid,suppvendcompany,voucherpaid,total,subtotal,pcamount,discamount,discpercent,feeamount,termsdiscdays,termsnetdays,termsdisc,voucherdate,vouchertime,invoiceduedate,invoicedate,creationdate from voucher" + where_sql + ' order by sid asc')
    cur_nzs = [ d[0].lower() for d in cur.description ]
    for r in cur.rows():
        r = dict(zip(cur_nzs, r))
        
        sid = r['sid']
        
        if r['datastate']:
            del_seq += 1
            mdb.query("delete from sync_vouchers where sid=%d" % (sid,))
            continue
        
        items = []
        sur.execute('select i.itemsid,i.porefsid,i.ponum,i.sorefsid,i.sonum,d.deptsid,d.vendsid,i.serialnum as snum,i.nunits,i.qty,i.origqty,i.price,i.pricetax,i.cost,i.unitofmeasure as uom,d.desc1,ifnull(ld.desc2,d.desc2,ld.desc2) as desc2,d.itemno,d.alu,d.upc from VoucherItem i left join VoucherItemDesc d on (i.sid=d.sid and i.itempos=d.itempos) left join VoucherItemLongDesc ld on (i.sid=ld.sid and i.itempos=ld.itempos) where i.sid=? order by i.itempos asc', (sid,))
        sur_nzs = [ d[0].lower() for d in sur.description ]
        item_sids = {}
        qty_count = orig_count = 0
        for rr in sur.rows():
            rr = dict(zip(sur_nzs, rr))
            item_sid = rr['itemsid']
            rr['nunits'] = round(float(rr['nunits']),5)
            orig = rr['origqty'] = round(float(rr['origqty']),5)
            qty = rr['qty'] = round(float(rr['qty']),5)
            rr['price'] = round(float(rr['price']),5)
            #rr['pricetax'] = round(float(rr['pricetax']),5)
            rr['cost'] = round(float(rr['cost']),5)
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
            orig_count += abs(orig)
            item_sids.setdefault(item_sid, True)
        
        global_js = json.dumps({
            'total': round(float(r['total']), 5),
            'subtotal': round(float(r['subtotal']), 5),
            'discamt': round(float(r['discamount']), 5),
            'discprc': round(float(r['discpercent']), 5),
            'feeamt': round(float(r['feeamount']), 5),
            'pcamt': r['pcamount'] and round(float(r['pcamount']), 5) or 0,
            'itemcount': len(item_sids),
            'qtycount': qty_count,
            'origcount': orig_count,
            'memo': r['comments'] or '',
            'termsdiscdays': r['termsdiscdays'],
            'termsnetdays': r['termsnetdays'],
            'termsdisc': round(float(r['termsdisc']), 5),
            'ponum': r['ponum'] or '',
            'invnum': r['invoicenumber'] or '',
            'vend': r['suppvendcompany'] or ''
        }, separators=(',',':'))
        
        rep_seq += 1
        sqlt = "(%d,%d,%s,%d,%d,'%s',%d,%d,%d,%d,'%s','%s')," % (
            sid,
            r['suppvendsid'],
            r['docrefsid'] == None and 'null' or "'%s'" % r['docrefsid'],
            (r['voucherpaid'] << 16) | (r['vouchertype'] << 8) | r['voucherstatus'],
            r['vouchernum'],
            mdb.escape_string(r['clerk'] and r['clerk'].encode('utf8') or ''),
            r['voucherdate'] and int(time.mktime(time.strptime(r['voucherdate'] + ' ' + r['vouchertime'].split('.')[0], '%Y-%m-%d %H:%M:%S'))) or 0,
            r['invoiceduedate'] and int(time.mktime(time.strptime(r['invoiceduedate'], '%Y-%m-%d'))) or 0,
            r['invoicedate'] and int(time.mktime(time.strptime(r['invoicedate'], '%Y-%m-%d'))) or 0,
            int(time.mktime(time.strptime(r['creationdate'].split('.')[0], '%Y-%m-%d %H:%M:%S'))),
            mdb.escape_string( global_js ),
            mdb.escape_string( json.dumps(items, separators=(',',':')) )
        )
        
        if len(sql) + len(sqlt) >= 1024 * (1024 - 1):
            print rep_seq
            sql = 'replace into sync_vouchers values ' + sql[:-1]
            mdb.query(sql)
            sql = ''
        sql += sqlt
    
    if sql:
        sql = 'replace into sync_vouchers values ' + sql[:-1]
        mdb.query(sql)
        sql = ''
    
    #if rep_seq or del_seq:
    #    if mode:
    #        mdb.query('optimize table sync_vouchers')
    #        mdb.use_result()
    
    print 'sync_vouchers: R(%d) D(%d)' % (rep_seq, del_seq)
    return rep_seq + del_seq


g_sync_cb = ('vouchers', sync_vouchers)

if __name__ == '__main__':
    #sync_receipts( (('receipt', -6172729321342464255),) )
    sync_main(g_sync_cb)


