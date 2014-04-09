import config
import datetime
import time
import cPickle
import json
import os
import db as mydb

mdb = mydb.db_mdb()
cur = mdb.cursor()


g_s = {}

cur.execute('select * from sync_receipts where sid_type=0 and (type&0xFF00)<0x0200')
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    
    items = json.loads(r['items_js'])
    glbs = json.loads(r['global_js'])
    
    rtype = (r['type'] >> 8) & 0xFF
    disc = (100 - glbs['discprc']) / 100
    
    total_price = 0
    total_cost = 0
    for t in items:
        if t['itemsid'] == 1000000005: continue
        total_price += t['price'] * t['qty']
        total_cost += t['cost'] * t['qty']

    total_price *= disc

    tp = time.localtime(r['order_date'])
    dt = time.mktime(datetime.date(tp.tm_year, tp.tm_mon, 1).timetuple())
    s = g_s.setdefault(dt, [0, 0, 0])
    if rtype > 0:
        s[0] -= 1
        s[1] -= total_price
        s[2] -= total_cost
    else:
        s[0] += 1
        s[1] += total_price
        s[2] += total_cost

cur.execute('select * from sorder where (ord_flag&8)!=0')
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    
    items = json.loads(r['ord_items_js'])
    glbs = json.loads(r['ord_global_js'])
    
    rtype = r['ord_flag'] & (1 << 1)
    disc = (100 - glbs['disc']) / 100
    
    total_price = 0
    total_cost = 0
    for t in items:
        total_price +=  t['in_price'] * t['in_qty']
        total_cost += t['prev_qty'][4] * t['in_base_qty']

    total_price *= disc

    tp = time.localtime(r['ord_order_date'])
    dt = time.mktime(datetime.date(tp.tm_year, tp.tm_mon, 1).timetuple())
    s = g_s.setdefault(dt, [0, 0, 0])
    if rtype > 0:
        s[0] -= 1
        s[1] -= total_price
        s[2] -= total_cost
    else:
        s[0] += 1
        s[1] += total_price
        s[2] += total_cost


s = g_s.items()
s.sort(key=lambda f_x:f_x[0])
cPickle.dump({'summary': s}, open(os.path.join(config.DATA_DIR, 'receipt_report.txt'), "wb"), 1)


