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


g_s = [{}, {}, {}]
g_n = [{}, {}, {}]
g_c = {}


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
    

    g_m = g_c.setdefault(r['cid'])
    if g_m == None: g_m = g_c[ r['cid'] ] = [{}, {}, {}]

    g_gs = (g_s, g_n, g_m)
    g_gt = ([], [], [])

    tp = time.localtime(r['order_date'])

    di = tp.tm_year * 10000 + tp.tm_mon * 100 + tp.tm_mday
    for i in range(len(g_gs)): g_gt[i].append( g_gs[i][0].setdefault(di, {}) )

    dt = datetime.date(*tp[:3]) - datetime.timedelta(tp.tm_wday)
    di = dt.year * 10000 + dt.month * 100 + dt.day
    for i in range(len(g_gs)): g_gt[i].append( g_gs[i][1].setdefault(di, {}) )

    di = tp.tm_year * 10000 + tp.tm_mon * 100 + 1
    for i in range(len(g_gs)): g_gt[i].append( g_gs[i][2].setdefault(di, {}) )

    r_clerk = (r['cashier'] or '').lower()
    r_clerk = USER_MAP.get(r_clerk, r_clerk)
    for nd in g_gt[1]: nd.setdefault(r_clerk, [0])[0] += 1

    for t in items:
        if t['itemsid'] == 1000000005: continue
        extprice = round(t['price'] * t['qty'] * disc, 5)
        extcost = round(t['cost'] * t['qty'], 5)
        if rtype > 0:
            extprice = -extprice
            extcost = -extcost

        if not extcost: extcost = extprice
        
        cate = (DEPTS.get(t['deptsid']) or [None, None])[1]
        if cate == None: cate = (ITEM_DEPTS.get(t['itemsid']) or [None, None])[1]
        cate = (cate or '').lower()

        clerk = (t['clerk'] or '').lower()
        clerk = USER_MAP.get(clerk, clerk)

        for i in (0, 2):
            cds = g_gt[i]
            for cd in cds:
                v_s = cd.setdefault(clerk, {}).setdefault(cate, [0, 0])
                v_s[0] += extprice
                v_s[1] += extcost


g_s_n = []
for cd in g_s:
    cd = cd.items()
    cd.sort(key=lambda f_x:f_x[0])
    g_s_n.append(cd)

g_n_n = []
for nd in g_n:
    nd = nd.items()
    nd.sort(key=lambda f_x:f_x[0])
    g_n_n.append(nd)

g_c_n = {}
for cid,g_m in g_c.items():
    g_m_n = []
    for md in g_m:
        md = md.items()
        md.sort(key=lambda f_x:f_x[0])
        g_m_n.append(md)
    g_c_n[cid] = g_m_n


datafile = os.path.join(config.APP_DIR, 'data', "daily_sale.txt")
cPickle.dump( {'s': g_s_n, 'n': g_n_n}, open(datafile, 'wb'), 1 )
print "Done", time.time() - CTS 
