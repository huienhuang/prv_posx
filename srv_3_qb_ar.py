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
    
    if r['is_paid_bool'] and pm_date:
        days = (datetime.date(*map(int, pm_date.split('/'))) - dt).days
    else:
        days = (cur_dt - dt).days
    
    g_invs[ r['transaction_id'] ] = (r['doc_num'], r['is_paid_bool'], dt.year * 10000 + dt.month * 100 + dt.day, days)
    s = g_dues.setdefault(dt.year * 100 + dt.month, [0, 0, 0, 0, 0])
    s[-1] += 1
    s[ min(max(int(days / 30), 0), 3) ] += 1

cPickle.dump({'invs': g_invs}, open(os.path.join(config.DATA_DIR, 'qb_ar_invs.txt'), "wb"), 1)
cPickle.dump({'dues': g_dues}, open(os.path.join(config.DATA_DIR, 'qb_ar_dues.txt'), "wb"), 1)


