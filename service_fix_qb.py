from service_base_v3 import srv_main
import time
import config
import datetime



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
	upd_users.sort(key=lambda f_x:f_x[0])

	for r in upd_users:
		pos_cur.execute('update customer set creditused=? where datastate=0 and sid=? and qblistid=?', (r[2], r[0], r[1]))
		pos_cur.execute("insert into changejournal values(default,'Customer',?,1,now(),'POSX', '-1')", (r[0],))
	pos_cur.execute('commit')


	return len(upd_users)


def main():
	srv_main( ((update_balance, 3000),) )

if __name__ == '__main__':
	main()
