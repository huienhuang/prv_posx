from sync_helper import *
import sys
import json
import time


def sync_items_hist(cj_data, mode=0):
    cur,sur = pos_db()
    mdb = sys_db()
    
    if mode:
        if mode == 1: mdb.query('delete from sync_items_hist')
        where_sql = ''
    else:
        sids = [ str(x[1]) for x in cj_data if x[0] and x[0].lower() == 'inventoryhistory' ]
        if not sids: return 0
        where_sql = ' where historysid in (%s)' % (','.join(sids),)

    rep_seq = del_seq = 0
    sql = ''
    cur.execute("select * from inventoryhistory" + where_sql)
    cur_nzs = [ d[0].lower() for d in cur.description ]
    for r in cur.rows():
        r = dict(zip(cur_nzs, r))
        
        rep_seq += 1
        sqlt = "(%d,0,%d,%d,%d,%d,'%s',%0.2f,%0.2f,%0.2f,%0.2f,%0.2f,%d)," % (
            r['historysid'],
            r['itemsid'],
            r['docsid'],
            r['docnumber'],
            (r['doctype'] << 8) | r['doctxnstatus'],
            mdb.escape_string((r['docdetails'] or u'').encode('utf8')),
            float(r['qtynew']),
            float(r['qtydiff']),
            float(r['costnew']),
            float(r['costdiff']),
            float(r['extprice']),
            int(time.mktime(time.strptime(r['docdate'].split('.')[0], '%Y-%m-%d %H:%M:%S'))),
        )
        
        if len(sql) + len(sqlt) >= 1024 * (1024 - 1):
            print rep_seq
            sql = 'replace into sync_items_hist values ' + sql[:-1]
            mdb.query(sql)
            sql = ''
        sql += sqlt
    
    if sql:
        sql = 'replace into sync_items_hist values ' + sql[:-1]
        mdb.query(sql)
        sql = ''
    
    #if rep_seq or del_seq:
    #    if mode:
    #        mdb.query('optimize table sync_items_hist')
    #        mdb.use_result()
    
    print 'sync_items_hist: R(%d)' % (rep_seq)
    return rep_seq + del_seq


g_sync_cb = ('items_hist', sync_items_hist)

if __name__ == '__main__': sync_main(g_sync_cb)

