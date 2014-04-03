import config
import db as mydb
import datetime
import time
import json
import cPickle
import os


mdb = mydb.db_mdb()
cur = mdb.cursor()

cur_tp = time.localtime()
cur_mon_ts = int(time.mktime(datetime.date(cur_tp.tm_year, cur_tp.tm_mon, 1).timetuple()))

g_cids = {}
cur.execute("select order_date,cid from sync_receipts where cid is not null and order_date < %s", (cur_mon_ts, ))
for r in cur.fetchall():
    tp = time.localtime(r[0])
    ts = int(time.mktime(datetime.date(tp.tm_year, tp.tm_mon, 1).timetuple()))
    cids = g_cids.setdefault(ts, set()).add(r[1])

active_counts = []
for k,v in sorted(g_cids.items(), key=lambda f_x: f_x[0]): active_counts.append((k, len(v)))

cPickle.dump({'active_counts': active_counts}, open(os.path.join(config.DATA_DIR, 'customer_report.txt'), 'wb'), 1)
