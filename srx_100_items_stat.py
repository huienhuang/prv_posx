import config
import datetime
import time
import cPickle
import json
import os
import db as mydb

mdb = mydb.db_mdb()
cur = mdb.cursor()

g_items = {}

cur.execute('select * from sync_receipts where sid_type=0 and (type&0xFF00)<0x0200')
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    
    items = json.loads(r['items_js'])
    glbs = json.loads(r['global_js'])

    store_id = glbs.get('store', 1)
    if store_id not in (1, 2): store_id = 1
    
    rtype = (r['type'] >> 8) & 0xFF
    
    disc = 1
    if glbs['subtotal']: disc = 1 - glbs['discamt'] / glbs['subtotal']
    
    tp = time.localtime(r['order_date'])
    for t in items:
        item = g_items.get(t['itemsid'])
        if not item: item = g_items[ t['itemsid'] ] = [set(), set(), {}, None]
        item[0].add(t['itemno'])
        item[1].add(t['desc1'])

        mk = tp.tm_year * 100 + tp.tm_mon
        stat = item[2].get(mk)
        if not stat: stat = item[2][mk] = [0, 0, 0, ([0, 0, 0], [0, 0, 0])]

        total_base_qty = t['nunits'] * t['qty']
        total_price =  t['price'] * t['qty'] * disc
        total_cost = t['cost'] * t['qty']
        
        if rtype > 0:
            total_base_qty = -total_base_qty
            total_price = -total_price
            total_cost = -total_cost
        
        stat[0] += total_base_qty
        stat[1] += total_price
        stat[2] += total_cost

        s_stat = stat[3][store_id - 1]
        s_stat[0] += total_base_qty
        s_stat[1] += total_price
        s_stat[2] += total_cost


cur.execute('select * from sorder where (ord_flag&8)!=0')
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    
    items = json.loads(r['ord_items_js'])
    glbs = json.loads(r['ord_global_js'])
    
    rtype = r['ord_flag'] & (1 << 1)
    disc = (100 - glbs['disc']) / 100
    
    tp = time.localtime(r['ord_order_date'])
    for t in items:
        item = g_items.get(t['id'])
        if not item: item = g_items[ t['id'] ] = [set(), set(), {}, None]
        item[0].add(t['num'])
        item[1].add(t['in_desc'])

        mk = tp.tm_year * 100 + tp.tm_mon
        stat = item[2].get(mk)
        if not stat: stat = item[2][mk] = [0, 0, 0, ([0, 0, 0], [0, 0, 0])]

        total_base_qty = t['in_base_qty']
        total_price =  t['in_price'] * t['in_qty'] * disc
        total_cost = t['prev_qty'][4] * total_base_qty
        
        if rtype > 0:
            total_base_qty = -total_base_qty
            total_price = -total_price
            total_cost = -total_cost
            
        stat[0] += total_base_qty
        stat[1] += total_price
        stat[2] += total_cost

        s_stat = stat[3][0]
        s_stat[0] += total_base_qty
        s_stat[1] += total_price
        s_stat[2] += total_cost


g_vendors = {}
g_item_nos = {}

cur.execute('select * from sync_items')
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    js = json.loads(r['detail'])

    g_item_nos[ r['sid'] ] = r['num']
    for v in js['vends']: g_vendors.setdefault(v[3], [v[0], set()])[1].add(r['sid'])

    item = g_items.get(r['sid'])
    if not item: continue
    l_qty = js['qty']
    item[3] = {
        'num': r['num'],
        'name': r['name'],
        'l_qty': l_qty,
        'status': r['status'],
        'deptsid': r['deptsid'],
    }

for item in g_items.values():
    item[0] = tuple(item[0])
    item[1] = tuple(item[1])
    d_status = item[2]
    item[2] = [ [f_k] + f_v for f_k,f_v in sorted(d_status.items(), key=lambda f_x:f_x[0]) ]


for v in g_vendors.values(): v[1] = sorted(v[1], key=lambda f_x: g_item_nos[f_x])


cPickle.dump(g_items, open(os.path.join(config.DATA_DIR, 'items_stat.txt'), 'wb'), 1)
cPickle.dump(g_vendors, open(os.path.join(config.DATA_DIR, 'items_vendors.txt'), 'wb'), 1)



print "Done"


