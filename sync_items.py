from sync_helper import *
import sys
import json
import const


def rf5(s): return rf(s, 5)

def sync_items(cj_data, mode=0):
    cur,sur = pos_db()
    mdb = sys_db()
    
    if mode:
        mdb.query('delete from sync_items_upcs')
        mdb.query('delete from sync_items')
        where_sql = 'i.datastate=0'
    else:
        sids = [ str(x[1]) for x in cj_data if x[0] and x[0].lower() == 'inventory' ]
        if not sids: return 0
        where_sql = 'i.itemsid in (%s)' % (','.join(sids),)
    
    cur.execute("select i.itemsid,i.datastate,i.itemno,i.deptsid,i.udf1,i.udf2,i.udf5,i.unitofmeasure,i.sellbyunit,i.orderbyunit,i.vendsid,i.vendname,i.alu,i.upc,i.companyohqty,i.qtystore1,i.qtystore2,i.custordqty,i.availqty,i.toto_o,i.cost,i.lastcost,i.desc1,ifnull(l.desc2,i.desc2,l.desc2) as desc2,i.price1,i.price2,i.price3,i.price4,i.price5,i.price6,i.cmpmin,i.reordernotnull from inventory i left join InventoryLongDesc l on i.itemsid=l.itemsid where " + where_sql)
    
    item_upcs = {}
    rep_seq = del_seq = 0
    sql = ''
    col_nzs = [ d[0].lower() for d in cur.description ]
    for r in cur.rows():
        r = dict(zip(col_nzs, r))
        
        itemsid = r['itemsid']
        if r['datastate']:
            del_seq += 1
            mdb.query("delete from sync_items_upcs where sid=%d" % (itemsid,))
            mdb.query("delete from sync_items where sid=%d" % (itemsid,))
            continue
        
        upc_lku = {}
        
        sur.execute('select price1,price2,price3,price4,price5,price6,alu,unitofmeasure,unitfactor,upc from InventoryUnits where itemsid=? order by uompos asc', (itemsid,))
        units = []
        obu_idx = sbu_idx = k = 0
        sell_by_unit = r['sellbyunit'] and r['sellbyunit'].lower() or None
        order_by_unit = r['orderbyunit'] and r['orderbyunit'].lower() or None
        for x in sur.fetchall():
            uom = x[7] or ''
            units.append( (map(rf2,x[:6]), x[6] or '', uom, rf2(x[8]), x[9] and str(x[9]) or '') )
            k += 1
            if sell_by_unit and sell_by_unit == uom.lower(): sbu_idx = k
            if order_by_unit and order_by_unit == uom.lower(): obu_idx = k
            if x[9]: upc_lku[ x[9] ] = k
            
        units.insert(0, (
            ( rf2(r['price1']), rf2(r['price2']), rf2(r['price3']), rf2(r['price4']), rf2(r['price5']), rf2(r['price6']) ),
            r['alu'] or '', r['unitofmeasure'] or '', 1, r['upc'] and str(r['upc']) or ''
            )
        )
        
        sur.execute('select vendname,alu,upc,ordercost,vendsid from InventoryVendor where itemsid=? and vendname is not null order by vendorpos asc', (itemsid,))
        vends = []
        costs = []
        for x in sur.fetchall():
            vends.append( (x[0] or '', x[1] or '', x[2] and str(x[2]) or '', x[4]) )
            costs.append( rf5(x[3]) )
            if x[2]: upc_lku[ x[2] ] = sbu_idx
        vends.insert(0, (r['vendname'] or '', '', '', r['vendsid']))
        costs.insert(0, rf5(r['lastcost']))
        
        if r['upc']: upc_lku[ r['upc'] ] = 0
        item_upcs[itemsid] = upc_lku
        
        r_cmpmin = None
        if r['reordernotnull']: r_cmpmin = rf2(r['cmpmin'])
        
        stores = [
            [rf2(r['companyohqty']), rf2(r['toto_o']), rf2(r['custordqty']), r_cmpmin],
            [rf2(r['qtystore1']), 0, 0, None],
            [rf2(r['qtystore2']), 0, 0, None]
        ]
        sur.execute('select store,orderedqty,custordqty,reorderpoint,reordernotnull from inventorystore where itemsid=?', (itemsid, ))
        for x in sur.fetchall():
            if x[0] < 1 or x[0] > 2: continue
            s = stores[ x[0] ]
            s[1] = rf2(x[1] or 0)
            s[2] = rf2(x[2] or 0)
            if x[4]: s[3] = rf2(x[3] or 0)

        jsd = {
            'default_uom_idx': sbu_idx,
            'order_uom_idx': obu_idx,
            'qty': (rf2(r['companyohqty']), rf2(r['custordqty']), rf2(r['availqty']), rf2(r['toto_o'])),
            'sqty': (rf2(r['qtystore1']), rf2(r['qtystore2'])),
            'units': units,
            'vends': vends,
            'desc1': r['desc1'].strip() or '',
            'stores': stores,
        }
        jsp = {
            'cost': rf5(r['cost']),
            'costs': costs,
        }
        
        lookup = set( [ unicode(r['itemno']) ] + [ x[1].lower().strip() for x in units if x[1] ] + [ x[1].lower().strip() for x in vends[1:] if x[1] ] )
        udfs = jsd['udfs'] = []
        if r['udf1']:
            s = r['udf1'].lower().strip()
            udfs.append(s)
            lookup.add(s)
        if r['udf2']:
            s = r['udf2'].lower().strip()
            udfs.append(s)
            lookup.add(s)
        lookup.discard(u'')
        
        desc2 = u''
        if r['desc2']:
            for x in r['desc2'].split(u'\n'):
                x = x.strip()
                if x: desc2 += x + u', '
        if desc2: desc2 = desc2[:-2]
        
        status = 0
        if r['udf5']:
            status = const.ITEM_D_STATUS.get(r['udf5'].lower().strip(), 0) & 0x0F
            if status == 1 and jsd['qty'][0] <= 0: status = 127
        
        rep_seq += 1
        sqlt = "(%d,%s,%d,%d,'%s','%s','%s','%s')," % (
            itemsid,
            r['deptsid'] == None and 'null' or r['deptsid'],
            status,
            r['itemno'],
            mdb.escape_string( u' '.join(lookup).encode('utf8') ),
            mdb.escape_string( desc2.encode('utf8') ),
            mdb.escape_string( json.dumps(jsd, separators=(',',':')) ),
            mdb.escape_string( json.dumps(jsp, separators=(',',':')) ),
        )
        
        if len(sql) + len(sqlt) >= 1024 * (1024 - 1):
            print rep_seq
            sql = 'replace into sync_items values ' + sql[:-1]
            mdb.query(sql)
            sql = ''
        sql += sqlt
        
    if sql:
        sql = 'replace into sync_items values ' + sql[:-1]
        mdb.query(sql)
        sql = ''
    
    #if rep_seq or del_seq:
    #    if mode:
    #        mdb.query('optimize table sync_items')
    #        mdb.use_result()
    
    if not mode:
        itemsids = item_upcs.keys()
        if itemsids:
            mdb.query('select * from sync_items_upcs where sid in (%s) order by sid asc' % (','.join(map(str, itemsids)),))
            for row in mdb.use_result().fetch_row(maxrows=0):
                sid,upc,old_idx = map(int, row)
                upcs = item_upcs[sid]
                idx = upcs.get(upc)
                if idx == None:
                    mdb.query('delete from sync_items_upcs where sid=%d and upc=%d' % (sid, upc))
                elif idx == old_idx:
                    del upcs[upc]
    
    for itemsid, upc_lku in item_upcs.items():
        for upc, uom_idx in upc_lku.items():
            sqlt = "(%d,%d,%d)," % (
                itemsid, upc, uom_idx
            )
            if len(sql) + len(sqlt) >= 1024 * (1024 - 1):
                sql = 'replace into sync_items_upcs values ' + sql[:-1]
                mdb.query(sql)
                sql = ''
            sql += sqlt
        
    if sql:
        sql = 'replace into sync_items_upcs values ' + sql[:-1]
        mdb.query(sql)
        sql = ''

    print 'sync_items: R(%d), D(%d)' % (rep_seq, del_seq)
    return rep_seq + del_seq


g_sync_cb = ('items', sync_items)

if __name__ == '__main__':
    #sync_items(None, 1)
    sync_main(g_sync_cb)


