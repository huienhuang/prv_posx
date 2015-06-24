import config
import datetime
import time
import cPickle
import json
import os
import db as mydb
import const

CTS = time.time()
mdb = mydb.db_mdb()
cur = mdb.cursor()


MON_INTVALS = (1, 3, 6)
g_c = [{}, {}, {}]


cur.execute('select sid,name from sync_customers')
g_z = dict(cur.fetchall())

cur.execute('select * from sync_receipts where sid_type=0 and (type&0xFF00)<0x0200 order by sid asc')
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    if r['cid'] == None or not g_z.has_key(r['cid']): continue
    
    items = json.loads(r['items_js'])
    glbs = json.loads(r['global_js'])
    
    rtype = (r['type'] >> 8) & 0xFF
    
    disc = 1
    if glbs['subtotal']: disc = 1 - glbs['discamt'] / glbs['subtotal']
    
    tp = time.localtime(r['order_date'])
    cds = []
    for i in range(3):
        mi = MON_INTVALS[i]
        mon = (tp.tm_mon - 1) / mi * mi + 1
        di = tp.tm_year * 10000 + mon * 100 + 1
        cds.append( g_c[i].setdefault(di, {}).setdefault(r['cid'], [0, 0]) )

    for t in items:
        if t['itemsid'] == 1000000005: continue
        extprice = t['price'] * t['qty'] * disc
        extcost = t['cost'] * t['qty']
        if rtype > 0:
            extprice = -extprice
            extcost = -extcost

        if not extcost: extcost = extprice

        for cd in cds:
            cd[0] += round(extprice, 5)
            cd[1] += round(extcost, 5)

g_c_n = []
for cd in g_c:
    cd = cd.items()
    cd.sort(key=lambda f_x:f_x[0])
    g_c_n.append(cd)


datafile = os.path.join(config.APP_DIR, 'data', "customer_sale.txt")
cPickle.dump( {'c': g_c_n, 'z': g_z}, open(datafile, 'wb'), 1 )
print "Done", time.time() - CTS
