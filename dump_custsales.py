import db as mydb
import time
import json
import datetime
import csv


g_custs = {}
INTVALS = ( (1, set()), (3, set()), (6, set()), (12, set()) )


mdb = mydb.db_mdb()
cur = mdb.cursor()


frm_ts = int(time.mktime(datetime.date(2014, 1, 1).timetuple()))
cur.execute('select * from sync_receipts where cid is not null and sid_type=0 and (type&0xFF00)<0x0200 and order_date>=%s', (
    frm_ts,
    )
)
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))

    items = json.loads(r['items_js'])
    glbs = json.loads(r['global_js'])
    
    rtype = (r['type'] >> 8) & 0xFF
    
    disc = 1
    if glbs['subtotal']: disc = 1 - glbs['discamt'] / glbs['subtotal']
    
    for t in items:
        if t['itemsid'] == 1000000005: continue
        extprice = t['price'] * t['qty'] * disc
        extcost = t['cost'] * t['qty']
        if rtype > 0:
            extprice = -extprice
            extcost = -extcost
        if not extcost: extcost = extprice

    lst = g_custs.get(r['cid'])
    if lst == None: lst = g_custs[ r['cid'] ] = [ {} for f_i in INTVALS ]

    tp = time.localtime(r['order_date'])
    for k in range(len(INTVALS)):
    	i,s = INTVALS[k]
    	if i == 1:
    		dt = tp.tm_year * 100 + tp.tm_mon
    	else:
    		dt = tp.tm_year * 100 + (tp.tm_mon - 1) / i * i + 1

    	s.add(dt)
    	lst[k].setdefault(dt, [0])[0] += extprice


cur.execute('select sid,name from sync_customers')
g_cust_nzs = dict(cur.fetchall())

custs = []
for cid,lst in g_custs.items():
	nz = g_cust_nzs.get(cid)
	if nz == None: continue

	custs.append([nz.encode('utf8'), cid, lst])

for k in range(len(INTVALS)):
    i,s = INTVALS[k]

    cw = csv.writer( open('customer_%s.csv' % (i,), 'wb') )
    l = sorted(s)

    cw.writerow( ['Name',] + l )

    for nz,cid,lst in custs:
    	ss = lst[k]
    	row = [nz] + ['%0.2f' % ss.get(f_d, [0])[0] for f_d in l]
    	cw.writerow( row )








