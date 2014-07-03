import config
import datetime
import time
import cPickle
import json
import os
import db as mydb
import const

mdb = mydb.db_mdb()
cur = mdb.cursor()

frm_ts = int(time.mktime(datetime.date(2014, 6, 1).timetuple()))
to_ts = int(time.mktime(datetime.date(2014, 7, 1).timetuple()))
cur.execute("select sr.cid,sc.name,count(*) from sync_receipts sr left join sync_customers sc on (sr.cid is not null and sr.cid=sc.sid) where sr.order_date>=%s and sr.order_date<%s and sr.cid is not null and sr.assoc='anthony' group by sr.cid", (
    frm_ts, to_ts
    )
)
nzs = cur.column_names
for r in cur:
    
    print r[1:]
    
    
    



