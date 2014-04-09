import config
import datetime
import time
import cPickle
import json
import os
import db as mydb
import json


mdb = mydb.db_mdb()
cur = mdb.cursor()


overall_ext_price = 0
overall_ext_cost = 0

g_items = {}

cur.execute('select * from sync_items')
nzs = cur.column_names
for r in cur.fetchall():
    r = dict(zip(nzs, r))
    
    jsd = json.loads(r['detail'])
    jsd2 = json.loads(r['detail2'])

    qty = jsd['qty'][0]
    price = jsd['units'][0][0][0]
    cost = jsd2['cost']
    
    ext_price = price * qty
    ext_cost = cost * qty
    
    overall_ext_price += ext_price
    overall_ext_cost += ext_cost
    
    g_items[ r['sid'] ] = (qty, price, cost)



tp = time.localtime()
dt = tp.tm_year * 10000 + tp.tm_mon * 100 + tp.tm_mday
cur.execute("replace into daily_inventory values(%s,%s,%s,%s)", (
    dt, overall_ext_price, overall_ext_cost, cPickle.dumps(g_items, 1)
    )
)





