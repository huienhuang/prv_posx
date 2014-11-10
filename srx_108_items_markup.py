import config
import datetime
import time
import cPickle
import json
import os
import db as mydb
import math

mdb = mydb.db_mdb()
cur = mdb.cursor()


g_item_vend = {}
cur.execute('select * from sync_vouchers where (status&0xFFFF)=0 order by voucherdate desc')
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))

    for t in json.loads(r['items_js']):
        if g_item_vend.has_key(t['itemsid']): continue
        g_item_vend[ t['itemsid'] ] = r['vend_sid']


l_items = []
cur.execute('select * from sync_items order by num asc')
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    jsd = json.loads(r['detail'])
    jsd2 = json.loads(r['detail2'])
    vends = jsd['vends']

    vend_sid = g_item_vend.get(r['sid'])
    vend_idx = 0

    for i in range(len(vends)):
        v = vends[i]
        if v[3] == vend_sid:
            vend_idx = i
            break

    vend = vends[ vend_idx ]
    cost = jsd2['costs'][vend_idx]

    price = [None, None, None, None, None, None]
    l_items.append( (r['sid'], vend[3], price) )
    if not cost: continue

    units = jsd['units']
    for u in units:
        p = u[0]
        if not u[3]: continue
        if u[3] != 1: p = [ round(f_x / u[3], 2) for f_x in p ]

        for i in range(6):
            if p[i] and (price[i] == None or p[i] < price[i]): price[i] = p[i]

    for i in range(6):
        if price[i] == None: continue
        price[i] = int(math.floor((price[i] - cost) / cost * 100))


fnz = os.path.join(config.DATA_DIR, 'items_markup.txt')
cPickle.dump(l_items, open(fnz, 'wb'), 1)

print "Done"


