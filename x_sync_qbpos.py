import config
import time
import datetime
import cPickle
from service_base_v3 import srv_main



g_seqs = {}
def get_last_seq(cur, ckey, dval=None):
	seq = g_seqs.get(ckey)
	if seq != None: return seq

	cur.execute('select cval from configv2 where ckey=%s', (ckey,))
	rows = cur.fetchall()
	if not rows:
		if dval != None:
			cur.execute('insert into configv2 values(%s,%s)', (ckey, dval))
			rows = [(dval,)]

	seq = g_seqs[ckey] = rows[0][0]
	return seq

def set_last_seq(cur, ckey, val):
	g_seqs[ckey] = val
	cur.execute('update configv2 set cval=%s where ckey=%s', (val, ckey))


FS_DOC_TYPES = {'invoice': 2, 'creditmemo': 3, 'receivepayment': 4}

def sync_pos_links(get_cur):
	cur_0 = get_cur('pos')
	cur_1 = get_cur('posx')

	last_seq = get_last_seq(cur_1, 'sync_fi_sessionsid', '')
	if not last_seq:
		last_seq = None
		cur_0.execute('select max(sessionsid) from FinancialSession where sessionfinish is not null')
	else:
		last_seq = int(last_seq)
		cur_0.execute('select max(sessionsid) from FinancialSession where sessionfinish is not null and sessionsid>?', (last_seq,))
	cur_seq = cur_0.fetchall()[0][0]
	if cur_seq == None: return
	cur_seq = int(cur_seq)

	links = []
	if last_seq == None:
		cur_0.execute('select pos_sid,fs_id,fs_doctype from financialdetail where sessionsid<=? and pos_doctype=5 order by sessionsid asc', (cur_seq,))
	else:
		cur_0.execute('select pos_sid,fs_id,fs_doctype from financialdetail where sessionsid>? and sessionsid<=? and pos_doctype=5 order by sessionsid asc', (last_seq, cur_seq))
	for r in cur_0.rows():
		pos_sid,fs_id,fs_doctype = r

		doc_id = FS_DOC_TYPES.get(fs_doctype.lower(), 0)
		if not doc_id: continue

		try:
			tid = int(fs_id.split('-')[0], 16)
		except:
			continue

		links.append( (pos_sid, tid, doc_id) )

	n = len(links)
	while links:
		cur_1.executemany('replace into qblinks values(%s, %s, %s)', links[:500])
		links = links[500:]

	set_last_seq(cur_1, 'sync_fi_sessionsid', str(cur_seq))

	print 'LINKS: %d, DT: %s' % (n, time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime()), )


def parse_date(s):
	try:
		ts = int(time.mktime(time.strptime(s, '%Y/%m/%d')))
	except:
		ts = 0

	return ts

def parse_float(s):
	try:
		v = round(float(s), 2)
	except:
		v = 0
	
	return v

QB_DOCS_TYPES = {'invoice': 2, 'credit_memo' : 3, 'received_payment': 4}#, ('sales_receipt', 'statement_charge', 'customer_refund')
def sync_qb_docs(get_cur):
	cur_0 = get_cur('qb')
	cur_1 = get_cur('posx')

	cts = time.time()

	last_seq = get_last_seq(cur_1, 'sync_qb_tbl_customer', '')
	where_s = ''
	if last_seq:
		t = last_seq
		t = '%s-%s-%s %s:%s:%s' % (t[:4], t[4:6], t[6:8], t[8:10], t[10:12], t[12:])
		where_s = " where db_modified_tms>'%s'" % (t, )

	recs = []
	cur_seq = None
	cur_0.execute('select customer_id,end_balance_amt,db_modified_tms from abmc_customer_internal' + where_s + ' order by db_modified_tms asc')
	for r in cur_0.rows():
		customer_id,end_balance_amt,db_modified_tms = r
		cur_seq = db_modified_tms
		recs.append( (customer_id, parse_float(end_balance_amt)) )

	if recs:
		n = len(recs)
		while recs:
			cur_1.executemany('replace into qbcustomers values(%s,%s)', recs[:500])
			recs = recs[500:]

		set_last_seq(cur_1, 'sync_qb_tbl_customer', str(cur_seq))

		ms = (time.time() - cts) * 1000
		print 'QBCustomer: %d, MS: %d, DT: %s' % (n, ms, time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime()), )


	for tnz, i in QB_DOCS_TYPES.items():
		cts = time.time()

		last_seq = get_last_seq(cur_1, 'sync_qb_tbl_' + tnz, '')

		add_fds = ''
		if i == 2: add_fds = ',h.is_paid_bool,h.due_date'

		where_s = ''
		if last_seq:
			t = last_seq
			t = '%s-%s-%s %s:%s:%s' % (t[:4], t[4:6], t[6:8], t[8:10], t[10:12], t[12:])
			where_s = " where h.db_modified_tms>'%s'" % (t, )

		cur_seq = None
		recs = []	
		cur_0.execute('select h.transaction_id,h.customer_id,h.db_modified_tms,h.doc_num,h.transaction_date,l.amount_amt,l.open_balance_amt'+add_fds+' from abmc_'+tnz+'_header h left join abmc_'+tnz+'_lineitem l on(h.transaction_id=l.transaction_id and h.target_id=l.target_id)'+where_s+' order by h.db_modified_tms asc')
		cur_nzs = [ d[0].lower() for d in cur_0.description ]
		for r in cur_0.rows():
			r = dict(zip(cur_nzs, r))

			cur_seq = r['db_modified_tms']

			if r['amount_amt'] == None:
				amt = 0
			else:
				amt = parse_float(r['amount_amt'])

			if r['open_balance_amt'] == None:
				bamt = amt
			else:
				bamt = parse_float(r['open_balance_amt'])

			is_paid = 0
			due_ts = 0
			if i == 2:
				is_paid = r['is_paid_bool'] and 1 or 0
				due_ts = parse_date(r['due_date'])

			recs.append((
				r['transaction_id'],
				i,
				r['customer_id'] or 0,
				r['doc_num'] or '',
				amt, bamt,
				parse_date(r['transaction_date']),
				is_paid, due_ts
				)
			)

		if not recs: continue

		n = len(recs)
		while recs:
			cur_1.executemany('replace into qbdocs values(%s,%s,%s,%s,%s,%s,%s,%s,%s)', recs[:500])
			recs = recs[500:]

		set_last_seq(cur_1, 'sync_qb_tbl_' + tnz, str(cur_seq))

		ms = (time.time() - cts) * 1000
		print 'QBDOCS(%s): %d, MS: %d, DT: %s' % (tnz, n, ms, time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime()), )




g_v2_sessionsid = None
def update_balance(get_cur):
	qb_cur = get_cur('qb')
	pos_cur = get_cur('pos')
	global g_v2_sessionsid

	pos_cur.execute('select first sessionsid,sessionfinish from FinancialSession order by sessionsid desc')
	row = pos_cur.fetchall()
	if not row or not row[0][1] or g_v2_sessionsid == row[0][0]: return

	cts = time.time()
	n = _update_balance(qb_cur, pos_cur)
	ms = (time.time() - cts) * 1000
	print 'update_balance: %d, MS: %d, DT: %s' % (n or 0, ms, time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime()), )

	g_v2_sessionsid = row[0][0]


def _update_balance(qb_cur, pos_cur):
	qb_users = {}
	qb_cur.execute("select list_ident,end_balance_amt from abmc_customer_internal")
	for r in qb_cur.fetchall():
		if not r[0]: continue
		qb_users[ r[0] ] = round(float(r[1]), 2)

	if not qb_users: return

	upd_users = []
	pos_cur.execute('select sid,qblistid,creditused,(select count(*) from receipt r where qbfsstatus!=1 and datastate=0 and r.billtosid=c.sid) as unsync from customer c where datastate=0 and useacccharge=1 and qblistid is not null and unsync<=0')
	for r in pos_cur.fetchall():
		sid,qblistid,creditused = r[:3]
		creditused = round(float(creditused), 2)
		balance = qb_users.get(qblistid)
		if balance == None or balance == creditused: continue

		upd_users.append([sid, qblistid, balance])

	if not upd_users: return
	upd_users.sort(lambda f_x:f_x[0])

	for r in upd_users:
		pos_cur.execute('update customer set creditused=? where datastate=0 and sid=? and qblistid=?', (r[2], r[0], r[1]))
		pos_cur.execute("insert into changejournal values(default,'Customer',?,1,now(),'POSX', '-1')", (r[0],))
	pos_cur.execute('commit')


	return len(upd_users)






def main():
	srv_main( ((sync_pos_links, 600), (sync_qb_docs, 8000), (update_balance, 3000)) )

if __name__ == '__main__':
    main()

