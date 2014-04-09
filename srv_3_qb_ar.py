import config
import re
import thread
import time
import datetime
import sqlanydb
import cPickle
import os


cur_tp = time.localtime()
cur_dt = datetime.date(cur_tp.tm_year, cur_tp.tm_mon, cur_tp.tm_mday)

db_qb = sqlanydb.connect(**config.sqlany_qb)
cur = db_qb.cursor()

g_invs = {}
g_dues = {}
cur.execute("select h.transaction_id,h.transaction_date,h.doc_num,l.amount_amt,h.is_paid_bool from abmc_invoice_header h left join abmc_invoice_lineitem l on(h.transaction_id=l.transaction_id and h.target_id=l.target_id)")
col_nzs = [ d[0].lower() for d in cur.description ]
for r in cur.fetchall():
    r = dict(zip(col_nzs, r))
    
    cur.execute("select max(transaction_date), sum(amount_amt) from abmc_transaction_link where transaction_id = ? and link_type in (3,4,5,22) and is_t1_source_bool=0", (r['transaction_id'],))
    rr = cur.fetchone()
    if rr:
        pm_date = rr[0] or None
        pm_amt = rr[1] and float(rr[1]) or 0
    else:
        pm_date = None
        pm_amt = 0
        
    dt = datetime.date(*map(int, r['transaction_date'].split('/')))
    if cur_dt.year == d[0] and cur_dt.month == d[1]: continue
    
    s = g_dues.setdefault(time.mktime(datetime.date(dt.year, dt.month, 1).timetuple()), [0, 0, 0, 0, 0])
    s[-1] += 1
    
    days = 0
    if r['is_paid_bool']:
        days = pm_date and (datetime.date(*map(int, pm_date.split('/'))) - dt).days or 0
        s[ min(max(int(days / 30), 0), 3) ] += 1
    
    g_invs[ r['transaction_id'] ] = (r['doc_num'], r['is_paid_bool'], time.mktime(dt.timetuple()), days)


dues = g_dues.items()
dues.sort(key=lambda f_x:f_x[0])

cPickle.dump({'invs': g_invs}, open(os.path.join(config.DATA_DIR, 'qb_ar_invs.txt'), "wb"), 1)
cPickle.dump({'dues': dues}, open(os.path.join(config.DATA_DIR, 'qb_ar_dues.txt'), "wb"), 1)


