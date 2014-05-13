"""

import mysql.connector
import config
import datetime
import time
import json
import csv


dbc = mysql.connector.connect(**config.mysql)
cur = dbc.cursor()

g_items = {}

frm_ts = int(time.mktime( datetime.date(2013, 1, 1).timetuple() ))
to_ts = int(time.mktime( datetime.date(2014, 5, 1).timetuple() ))


cur.execute('select * from sync_receipts where order_date>=%s and order_date<%s and sid_type=0 and (type&0xFF00)<0x0200', (frm_ts, to_ts))
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    
    items = json.loads(r['items_js'])
    glbs = json.loads(r['global_js'])
    
    rtype = (r['type'] >> 8) & 0xFF
    disc = (100 - glbs['discprc']) / 100
    
    tp = time.localtime(r['order_date'])
    for t in items:
        #stat = g_items.setdefault(t['itemsid'], {}).setdefault('%04d-%02d' % (tp.tm_year, tp.tm_mon), [0, 0, 0])
        stat = g_items.setdefault(t['itemsid'], {}).setdefault('2013 To Now', [0, 0, 0])
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
    

cur.execute('select * from sorder where ord_order_date>=%s and ord_order_date<%s and (ord_flag&8)!=0', (frm_ts, to_ts))
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    
    items = json.loads(r['ord_items_js'])
    glbs = json.loads(r['ord_global_js'])
    
    rtype = r['ord_flag'] & (1 << 1)
    disc = (100 - glbs['disc']) / 100
    
    tp = time.localtime(r['ord_order_date'])
    for t in items:
        #stat = g_items.setdefault(t['id'], {}).setdefault('%04d-%02d' % (tp.tm_year, tp.tm_mon), [0, 0, 0])
        stat = g_items.setdefault(t['id'], {}).setdefault('2013 To Now', [0, 0, 0])
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

m_hdr = ['2013 To Now']
#for i in range(1, 13): m_hdr.append('%04d-%02d' % (2013, i))


hdr = ['#', 'Name', 'OH', 'PC', 'Cost', 'RegularPrice', 'Wholesale 1', 'Wholesale 2', 'Sold', 'SaleOfSold', 'CostOfSold', 'Mrgn']
#for i in m_hdr:
#    hdr.append( '%ssold' % (i[-2:],) )
#    hdr.append( '%ssale' % (i[-2:],) )
#    hdr.append( '%scost' % (i[-2:],) )
#    hdr.append( '%smrgn' % (i[-2:],) )
    
data = [hdr]
cur.execute('select * from sync_items order by num')
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))

    detail = json.loads(r['detail'])
    detail2 = json.loads(r['detail2'])
    units = detail['units']
    uom = units[ detail['default_uom_idx'] ]
    qtys = detail['qty']
    
    if uom[3] == 0:
        print 'Zero Factor', r
        continue
    
    OH = qtys[0] / uom[3]
    PC = qtys[3] / uom[3]
    
    row = [str(r['num']), r['name'] or '', '%0.1f' % (OH,), '%0.1f' % (PC,),
           '%0.2f' % (detail2['cost'] * uom[3],),
           '%0.2f' % (uom[0][0],),
           '%0.2f' % (uom[0][1],),
           '%0.2f' % (uom[0][2],),
           ]
    stats = g_items.get(r['sid'], {})
    for i in m_hdr:
        stat = stats.get(i)
        if stat:
            row.append( '%0.2f' % (stat[0] / uom[3], ) )
            row.append( '%0.2f' % stat[1] )
            row.append( '%0.2f' % stat[2] )
            row.append( '%0.2f' % (stat[1] - stat[2], ) )
        else:
            row.append( '' )
            row.append( '' )
            row.append( '' )
            row.append( '' )
    data.append(row)

wt = csv.writer( open('data.csv', 'wb') )
for r in data: wt.writerow(r)

"""



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

frm_dt = datetime.date(2014, 5, 12)
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
    disc = (100 - glbs['discprc']) / 100
    
    for t in items:
        if t['itemsid'] == 1000000005: continue
        
        t_baseqty = t['qty'] * t['nunits']
        t_price = t['qty'] * t['price'] * disc
        t_cost = t['qty'] * t['cost']
        
        dept_nz = DEPTS.get(t['deptsid'], '')
        if dept_nz != 'd-container & tray': continue
        
        d = g_depts.setdefault(dept_nz, [0, 0, 0, 0, 0, 0])
        if rtype > 0:
            print t_baseqty, r['num']
            d[3] -= t_baseqty
            d[5] -= t_price
            d[4] -= t_cost
        else:
            d[3] += t_baseqty
            d[5] += t_price
            d[4] += t_cost
    


print g_depts







