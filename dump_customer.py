import config
import datetime
import time
import json
import db as mydb
import csv

mdb = mydb.db_mdb()
cur = mdb.cursor()


frm_ts = int(time.mktime(datetime.date(2011, 1, 1).timetuple()))
to_ts = int(time.mktime(datetime.date(2013, 1, 1).timetuple()))
cid = -7777123475998736127


item_lst = []

cur.execute('select * from sync_receipts where sid_type=0 and (type&0xFF00)<0x0200 and order_date>=%s and order_date<%s and cid=%s order by sid asc', (
    frm_ts, to_ts, cid
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
        
        qty = t['qty']
        if rtype > 0: qty = -qty
        
        extprice = t['price'] * qty * disc
        extpricetax = t['pricetax'] * qty * disc
        
        item_lst.append((
            r['num'],
            time.strftime("%m/%d/%Y", time.localtime(r['order_date'])),
            t['itemno'],
            t['desc1'],
            '%0.1f' % (qty,),
            '%0.2f' % (extprice,),
            '%0.2f' % (extpricetax,),
        ))


cw = csv.writer( open("items.csv", "wb") )

for i in item_lst: cw.writerow(i)




