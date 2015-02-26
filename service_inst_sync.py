from service_base_v2 import srv_main
import json
import time
import config
import cPickle
import urllib2
import base64
import hashlib
import gzip
import cStringIO
import datetime


SNAPSHOT_CFNS = [u'Type', u'Title', u'FName', u'LName', u'Company', u'Address1', u'Address2', u'City', u'State', u'ZIP', u'Country', u'ShipAddrName', u'ShipCompany', u'ShipFullName', u'ShipAddress', u'ShipAddress2', u'ShipCity', u'ShipState', u'ShipZIP', u'ShipCountry', u'Phone1', u'Phone2', u'Phone3', u'Phone4', u'Email', u'Comments', u'UDF1', u'UDF2', u'UDF3', u'UDF4', u'UDF5', u'UDF6', u'UDF7', u'TaxArea', u'PriceLevel', u'DiscType', u'TrackRewards', u'CustomerID', u'WebNumber', u'WebFullNumber', u'EmailNotify', u'AR', u'UseAccCharge', u'AcceptChecks', u'DefaultShipTo', u'NoShipToBill', u'CreditLimit', u'DiscAllowed']

def gen_auth():
	ts_idx = int(int(time.time()) / 3600)

	pre_auth = hashlib.md5('%s%s%s%s' % (config.inst_sync_auth[1], config.secret_code, config.inst_sync_auth[0], config.inst_sync_auth[2])).digest()
	auth = hashlib.md5('%s%s%s' % (pre_auth, config.secret_code_v1, ts_idx)).hexdigest()

	return '%s:%s' % (config.inst_sync_auth[0], auth)

def get_remote_customer_chgs(seq):
	req = urllib2.Request('http://%s/posx/sys?fn=get_cust_chg&last_id=%d' % (config.inst_sync_auth[3], seq,))
	req.add_header('Accept-Encoding', 'gzip, deflate, sdch')
	req.add_header('Cookie', '__auth__="%s"' % (gen_auth(),))
	r = urllib2.urlopen(req)
	s = cStringIO.StringIO(r.read())
	r.close()

	z = gzip.GzipFile(fileobj=s)
	dd = z.read()
	try:
		js = cPickle.loads(dd)
	except:
		print dd
		raise
	z.close()

	return js

def get_remote_customer_inst_sync_last_id(cur):
	global g_sc_last_id
	if g_sc_last_id == None:
		cur.execute('select cval from config where cid=%s', (config.cid__inst_sync_customer_last_id, ))
		rs = cur.fetchall()
		if rs:
			g_sc_last_id = int(rs[0][0])
		else:
			g_sc_last_id = 0

	return g_sc_last_id

def set_remote_customer_inst_sync_last_id(cur, last_id):
	global g_sc_last_id
	if g_sc_last_id >= last_id: return
	g_sc_last_id = last_id
	cur.execute('update config set cval=%s where cid=%s', (g_sc_last_id, config.cid__inst_sync_customer_last_id))

g_sc_last_id = None
def inst_sync_customer(cur):
	cts = time.time()
	last_id = get_remote_customer_inst_sync_last_id(cur[0])
	chg,lts,cur_last_id = get_remote_customer_chgs(last_id)
	n = None
	if chg:
		print ">CHG: ", len(chg),
		n = _inst_sync_customer(cur, chg, lts)
		print "Done"
	set_remote_customer_inst_sync_last_id(cur[0], cur_last_id)
	if n == None: return
	print "DT: %s, LEN: %d, SECS: %0.3f" % (str(datetime.datetime.now()), n, time.time() - cts)

def _inst_sync_customer(cur, chg, lts):
	s_sids = ','.join([str(f_k) for f_k in chg.keys()])

	d_last_chg = {}
	cur[0].execute("select * from sync_customer_chg where ts>=%s and sid in (%s) order by id desc" % (lts, s_sids))
	for r in cur[0].fetchall():
		d = d_last_chg.setdefault(r[1], {})
		for k,v in cPickle.loads(r[3]):
			if d.has_key(k): continue
			d[k] = r[2]

	cs = {}
	cur[0].execute("select * from sync_customer_snapshots where sid in (%s)" % (s_sids, ))
	for r in cur[0].fetchall(): cs[ r[0] ] = (r[1], cPickle.loads(r[2]))

	lst = []
	for sid,fchg in sorted(chg.items(), key=lambda f_x:f_x[0]):
		f = d_last_chg.get(sid, {})
		c = cs.get(sid)
		if not c: continue

		l = []
		for k,v in fchg.items():
			#default flavor if == ?
			if c[1][k] == v[1] or f.has_key(k) and f[k] >= v[0]:
				continue
			else:
				l.append( (k, v[1]) )
		if l: lst.append( (sid, l) )

	if not lst: return

	try:
		for sid,flst in lst:
			#print sid, flst
			qs = []
			qv = []
			c = cs.get(sid)[1]
			for v in flst:
				qs.append('%s=?' % (SNAPSHOT_CFNS[v[0]],))
				qv.append(v[1])
				c[v[0]] = v[1]

			qv.append(sid)
			cur[0].execute('update sync_customer_snapshots set js=%s where sid=%s', (cPickle.dumps(c, 1), sid))
			cur[1].execute('update customer set %s where sid=? and datastate=0' % (','.join(qs),), qv)
			cur[1].execute("insert into changejournal values(default,'Customer',?,1,now(),'POSX', '-1')", (sid,))

		cur[1].execute('commit')

	except:
		cur[1].execute('rollback')
		raise

	return len(lst)


def main():
	srv_main( ((inst_sync_customer, 1000),) )

if __name__ == '__main__':
	main()

