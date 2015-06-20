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

cur.execute("select cval from configv2 where ckey='departments' limit 1")
DEPTS = {}
for x in cPickle.loads( cur.fetchall()[0][0] ):
    cate = const.ITEM_D_DEPT.get(x[0].lower())
    DEPTS[x[1]] = (x[0], cate)

ITEM_DEPTS = {}
cur.execute('select sid,deptsid from sync_items')
for r in cur.fetchall(): ITEM_DEPTS[r[0]] = DEPTS.get(r[1])

USER_MAP = {
    'sales1': 'ray',
    'sales2': 'anthony',
    'sales3': 'joe',
    'sales8': 'nicole',
    'sales5': 'jimmy',
    'sales6': 'sally',
}


g_c = [{}, {}, {}]
g_z = {}


frm_ts = int(time.mktime(datetime.date(2015, 1, 1).timetuple()))
cur.execute('select * from sync_receipts where sid_type=0 and (type&0xFF00)<0x0200 and order_date>=%s', (frm_ts, ))
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    
    items = json.loads(r['items_js'])
    glbs = json.loads(r['global_js'])
    
    rtype = (r['type'] >> 8) & 0xFF
    
    disc = 1
    if glbs['subtotal']: disc = 1 - glbs['discamt'] / glbs['subtotal']
    
    cid = r['cid']
    if cid != None:
        cz = glbs.get('customer', {})
        g_z[cid] = cz.get('company') or cz.get('name') or ''

    tp = time.localtime(r['order_date'])

    di = tp.tm_year * 10000 + tp.tm_mon * 100 + tp.tm_mday
    d0 = g_c[0].setdefault(di, {})

    dt = datetime.date(*tp[:3]) - datetime.timedelta(tp.tm_wday)
    di = dt.year * 10000 + dt.month * 100 + dt.day
    d1 = g_c[1].setdefault(di, {})

    di = tp.tm_year * 10000 + tp.tm_mon * 100 + 1
    d2 = g_c[2].setdefault(di, {})

    cds = (d0, d1, d2)
    for t in items:
        if t['itemsid'] == 1000000005: continue
        extprice = t['price'] * t['qty'] * disc
        extcost = t['cost'] * t['qty']
        if rtype > 0:
            extprice = -extprice
            extcost = -extcost

        if not extcost: extcost = extprice
        
        cate = (DEPTS.get(t['deptsid']) or [None, None])[1]
        if cate == None: cate = (ITEM_DEPTS.get(t['itemsid']) or [None, None])[1]
        cate = (cate or '').lower()

        clerk = (t['clerk'] or '').lower()
        clerk = USER_MAP.get(clerk, clerk)

        for cd in cds:
            v_s = cd.setdefault(clerk, {}).setdefault(cid, {}).setdefault(cate, [0, 0])
            v_s[0] += round(extprice, 5)
            v_s[1] += round(extcost, 5)

g_c_n = []
for cd in g_c:
    cd = cd.items()
    cd.sort(key=lambda f_x:f_x[0])
    g_c_n.append(cd)


datafile = os.path.join(config.APP_DIR, 'data', "daily_sale_2.txt")
cPickle.dump( {'c': g_c_n, 'z': g_z}, open(datafile, 'wb'), 1 )
print "Done", time.time() - CTS
