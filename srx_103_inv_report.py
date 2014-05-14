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

g_depts = {}
g_items = {}

overall_ext_price = overall_ext_cost = 0

cur.execute("select cval from configv2 where ckey='departments' limit 1")
DEPTS = dict([(f_x[1], f_x[0]) for f_x in cPickle.loads( cur.fetchall()[0][0] )])

cur.execute('select * from sync_items')
nzs = cur.column_names
for r in cur.fetchall():
    r = dict(zip(nzs, r))
    
    jsd = json.loads(r['detail'])
    jsd2 = json.loads(r['detail2'])

    qty = jsd['qty'][0]
    price = jsd['units'][0][0][0]
    cost = jsd2['cost']
    
    g_items[ r['sid'] ] = (qty, price, cost)
    
    ext_price = price * qty
    ext_cost = cost * qty
    
    d = g_depts.setdefault(DEPTS.get(r['deptsid'], ''), [0, 0, 0, 0, 0, 0])
    d[0] += qty
    d[2] += ext_price
    d[1] += ext_cost
    
    overall_ext_price += ext_price
    overall_ext_cost += ext_cost



tp = time.localtime()
#frm_dt = datetime.date(2014, 5, 12)
frm_dt = datetime.date(tp.tm_year, tp.tm_mon, tp.tm_mday)
frm_ts = int(time.mktime(frm_dt.timetuple()))
to_dt = frm_dt + datetime.timedelta(1)
to_ts = int(time.mktime(to_dt.timetuple()))

cur.execute('select * from sync_receipts where sid_type=0 and (type&0xFF00)<0x0200 and order_date>=%s and order_date<%s', (
    frm_ts, to_ts
    )
)
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    
    items = json.loads(r['items_js'])
    glbs = json.loads(r['global_js'])
    
    rtype = (r['type'] >> 8) & 0xFF
    rstatus = r['type'] & 0xFF
    disc = (100 - glbs['discprc']) / 100
    
    for t in items:
        if t['itemsid'] == 1000000005: continue
        
        t_baseqty = t['qty'] * t['nunits']
        t_price = t['qty'] * t['price'] * disc
        t_cost = t['qty'] * t['cost']
        
        d = g_depts.setdefault(DEPTS.get(t['deptsid'], ''), [0, 0, 0, 0, 0, 0])
        """
        if rtype > 0:
            pass
            d[3] -= t_baseqty
            d[5] -= t_price
            d[4] -= t_cost
        else:
            d[3] += t_baseqty
            d[5] += t_price
            d[4] += t_cost
        """
        if rstatus == 0:
            d[3] += t_baseqty
            d[5] += t_price
            d[4] += t_cost
        
cur.execute("replace into daily_inventory values(%s,%s,%s,%s)", (
    frm_ts, overall_ext_price, overall_ext_cost, cPickle.dumps((g_items, g_depts), 1)
    )
)



