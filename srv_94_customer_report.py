import config
import db as mydb
import datetime
import time
import json

mdb = mydb.db_mdb()
cur = mdb.cursor()


cid_a_ts = int(time.time()) - 3600 * 24 * 90
cid_b_ts = int(time.time()) - 3600 * 24 * 360

cur.execute("select distinct cid from sync_receipts where cid is not null and order_date >= %s", (cid_a_ts,))
d_cid_a = cur.fetchall()

cur.execute("select distinct cid from sync_receipts where cid is not null and order_date >= %s", (cid_b_ts,))
d_cid_b = cur.fetchall()


print round(float(len(d_cid_a)) / len(d_cid_b), 2)

