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

lst = sorted(g_cids.items(), key=lambda f_x: f_x[0])
if lst:
    m_min = time.localtime(lst[0][0])
    m_min = m_min.tm_year * 12 + m_min.tm_mon
    m_max = time.localtime(lst[-1][0])
    m_max = m_max.tm_year * 12 + m_max.tm_mon
    new_lst = [None,] * (m_max - m_min + 1)
    
active_counts = []
for k,v in lst:
    active_counts.append((k, len(v)))
    tp = time.localtime(k)
    new_lst[ tp.tm_year * 12 + tp.tm_mon - m_min ] = (k, v)

retention_rate = []
for i in range(len(new_lst)):
    u = new_lst[i]
    if u == None: continue
    k,v = u
    
    s = max(i - 14, 0)
    e = i - 2
    b = set()
    while s < e:
        w = new_lst[s]
        s += 1
        if w == None: continue
        b = b.union(w[1])
    
    s = max(i - 2, 0)
    a = v
    while s < i:
        w = new_lst[s]
        s += 1
        if w == None: continue
        a = a.union(w[1])
    c = a.intersection(b)
    
    retention_rate.append( (k, (len(b), len(a), len(c)) ) )
    

cPickle.dump({'active_counts': active_counts, 'retention_rate': retention_rate}, open(os.path.join(config.DATA_DIR, 'customer_report.txt'), 'wb'), 1)


