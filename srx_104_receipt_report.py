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
g_c = {}

cur.execute('select sr.*,(select count(*) from deliveryv2_receipt where num=sr.num and d_excluded=0) as is_delivery from sync_receipts sr where sr.sid_type=0 and (sr.type&0xFF00)<0x0200')
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    
    items = json.loads(r['items_js'])
    glbs = json.loads(r['global_js'])
    
    rtype = (r['type'] >> 8) & 0xFF
    
    disc = 1
    if glbs['subtotal']: disc = 1 - glbs['discamt'] / glbs['subtotal']
    
    total_price = 0
    total_cost = 0
    for t in items:
        if t['itemsid'] == 1000000005: continue
        total_price += t['price'] * t['qty']
        total_cost += t['cost'] * t['qty']

    total_price *= disc

    tp = time.localtime(r['order_date'])
    dt = int(time.mktime(datetime.date(tp.tm_year, tp.tm_mon, 1).timetuple()))
    s = g_s.setdefault(dt, [0, 0, 0, 0, 0, 0, None, 0, 0])
    
    s_t_qty = 1
    s_t_price = total_price
    s_t_cost = total_cost
    if rtype > 0:
        s_t_qty = -s_t_qty
        s_t_price = -s_t_price
        s_t_cost = -s_t_cost
    
    s[0] += s_t_qty
    s[1] += s_t_price
    s[2] += s_t_cost
    s[7] += 1
    if r['is_delivery']:
        s[3] += s_t_qty
        s[4] += s_t_price
        s[5] += s_t_cost
        s[8] += 1
  
    if r['cid'] != None:
        g_c.setdefault(r['cid'], {}).setdefault(dt, [0])[0] += s_t_price
  
        
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
    dt = int(time.mktime(datetime.date(tp.tm_year, tp.tm_mon, 1).timetuple()))
    s = g_s.setdefault(dt, [0, 0, 0, 0, 0, 0, None, 0, 0])
    if rtype > 0:
        s[0] -= 1
        s[1] -= total_price
        s[2] -= total_cost
    else:
        s[0] += 1
        s[1] += total_price
        s[2] += total_cost

    s[7] += 1


for k, v in g_s.items():
    cur.execute('select di_price,di_cost from daily_inventory where di_ts = %s', (k,))
    rows = cur.fetchall()
    if rows: v[6] = rows[0]

s = g_s.items()
s.sort(key=lambda f_x:f_x[0])
g_c = dict([(f_k, sorted(f_v.items(), key=lambda f_x:f_x[0])) for f_k,f_v in g_c.items()])
cPickle.dump({'summary': s, 'customer': g_c}, open(os.path.join(config.DATA_DIR, 'receipt_report.txt'), "wb"), 1)


