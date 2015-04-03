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
import TinyServer
import Queue
import thread
import db
import traceback
#import QBPOS
import zlib
import mysql.connector as MySQL
import sqlanydb


def ri(s): return int(math.floor(float(s)))
def rf(s, n=0): return config.round_ex(float(s), n)
def rf2(s): return rf(s, 2)



class QBClient(TinyServer.TinyAsyncMsgClient):
	def __init__(self):
		TinyServer.TinyAsyncMsgClient.__init__(self, config.inst_sync_cfg['remote'])

	def call_fn(self, fn, arg):
		p = cPickle.dumps({'fn': fn, 'arg': arg, 'auth': config.inst_sync_cfg['auth']}, 1)
		self.send_packet(zlib.compress(p, 9))

		p = zlib.decompress( self.recv_packet() )
		return cPickle.loads(p)['ret']


class QBServer(TinyServer.TinyAsyncMsgServer):
	def __init__(self):
		TinyServer.TinyAsyncMsgServer.__init__(self, config.inst_sync_cfg['server'])

		self.qmsg = Queue.Queue()
		self.dbc = None
		self.qbc = None
		self.pdb = None

		thread.start_new_thread(self.msg_handler, ())

	def get_dbc(self):
		if self.dbc != None: return self.dbc
		self.dbc = db.db_mdb()
		print "MYSQL Connected"
		return self.dbc

	def get_pdb(self):
		if self.pdb != None: return self.pdb
		self.pdb = sqlanydb.connect(**config.sqlany_pos_server)
		#cur = pdb.cursor()
		#cur.execute("SET TEMPORARY OPTION CONNECTION_AUTHENTICATION='Company=Intuit Inc.;Application=QuickBooks Point of Sale;Signature=000fa55157edb8e14d818eb4fe3db41447146f1571g7262d341128bbd2768e586a0b43d5568a6bb52cc'")
		print 'PDB Connected'
		return self.pdb

	def get_qbc(self):
		if self.qbc != None: return self.qbc
		g_cfg = config.qbpos_cfg
		self.qbc = QBPOS.OpenConnection(g_cfg["computer"], g_cfg["company"], "8")
		print "QBC Connected"
		return self.qbc

	def msg_handler(self):
		while True:
			s, p = self.qmsg.get()
			ret = None
			err = -1
			err_s = None
			try:
				raddr = s.getpeername()
				if raddr[0] == config.inst_sync_cfg['remote'][0]:
					p = cPickle.loads(p)
					if p['auth'] == config.inst_sync_cfg['auth']:
						try:
							if p['fn'] == 'get_cust_chg':
								ret = self.fn_get_cust_chg(p['arg'])
							elif p['fn'] == 'get_remote_customer':
								ret = self.fn_get_remote_customer(p['arg'])
							elif p['fn'] == 'get_customer':
								ret = self.fn_get_customer(p['arg'])
							elif p['fn'] == 'get_item_units':
								ret = self.fn_get_item_units(p['arg'])

						except MySQL.errors.Error, e:
							self.dbc = None
							raise
						except sqlanydb.Error, e:
							self.pdb = None
							raise
						except QBPOS.Error, e:
							self.qbc = None
							raise
						err = 0
					else:
						err_s = 'AUTH ERROR'
				else:
					err_s = 'ADDR ERROR'

			except Exception, e:
				es = traceback.format_exc()
				err_s = str(es)
				print err_s

			self.append_response(s, zlib.compress(cPickle.dumps({'err': err, 'err_s': err_s, 'ret': ret}, 1), 9) )
			self.qmsg.task_done()

 
	def process_request(self, s, p):
		try:
			p = zlib.decompress(p)
			self.qmsg.put( (s, p) )
		except Exception, e:
			print traceback.format_exc()

	def fn_get_cust_chg(self, p):
		last_id = p.get('last_id') or 0

		cur = self.get_dbc().cursor()
		cur.execute("select * from sync_customer_chg where id>%s order by id asc limit 100", (last_id,))
		d = {}
		lts = 0

		rows = list(reversed(cur.fetchall()))
		if rows:
			last_id = rows[0][0]
			lts = rows[0][2]

		for r in rows:
			sid,ts,js = r[1:]
			js = cPickle.loads(js)

			l = d.setdefault(sid, {})
			for i,v in js:
				if l.has_key(i): continue
				l[i] = (ts, v)
				if ts < lts: lts = ts

		return (d, lts, last_id)

	def fn_get_remote_customer(self, p):
		ret = {}

		cur = self.get_pdb().cursor()
		cur.execute('select * from customer where sid=?', (p['sid'],))
		r = cur.fetchall()
		if not r: return None

		ret['customer'] = r[0]
		cur.execute('select * from customerkeywords where sid=?', (p['sid'],))
		ret['customerkeywords'] = cur.fetchall()
		cur.execute('select * from customeraddress where sid=?', (p['sid'],))
		ret['customeraddress'] = cur.fetchall()

		return ret

	def fn_get_customer(self, p):
		xml = '<?xml version="1.0" ?><?qbposxml version="3.0"?><QBPOSXML><QBPOSXMLMsgsRq onError="stopOnError"><CustomerQueryRq><ListID>%s</ListID></CustomerQueryRq></QBPOSXMLMsgsRq></QBPOSXML>' % (p['sid'],)
		return QBPOS.ProcessRequest(self.get_qbc(), xml.decode('utf8'))

	def fn_get_item_units(self, p):
		ret = {}
		cur = self.get_pdb().cursor()
		cur.execute('select * from inventory where datastate=0')
		col_nzs = [ d[0].lower() for d in cur.description ]
		for r in cur.rows():
			r = dict(zip(col_nzs, r))

			units = []
			units.append([
				[ rf2(r['price1']), rf2(r['price2']), rf2(r['price3']), rf2(r['price4']), rf2(r['price5']), rf2(r['price6']) ],
				r['alu'] or '', r['unitofmeasure'] or '', 1, r['upc'] and str(r['upc']) or ''
			])

			ret[ r['itemsid'] ] = units


		cur.execute('select * from inventoryunits order by uompos asc')
		col_nzs = [ d[0].lower() for d in cur.description ]
		for r in cur.rows():
			r = dict(zip(col_nzs, r))

			u = [
				[ rf2(r['price1']), rf2(r['price2']), rf2(r['price3']), rf2(r['price4']), rf2(r['price5']), rf2(r['price6']) ],
				r['alu'] or '', r['unitofmeasure'] or '', rf2(r['unitfactor']), r['upc'] and str(r['upc']) or ''
			]

			ret.get(r['itemsid'], []).append(u)


		return ret


SNAPSHOT_CFNS = [u'Type', u'Title', u'FName', u'LName', u'Company', u'Address1', u'Address2', u'City', u'State', u'ZIP', u'Country', u'ShipAddrName', u'ShipCompany', u'ShipFullName', u'ShipAddress', u'ShipAddress2', u'ShipCity', u'ShipState', u'ShipZIP', u'ShipCountry', u'Phone1', u'Phone2', u'Phone3', u'Phone4', u'Email', u'Comments', u'UDF1', u'UDF2', u'UDF3', u'UDF4', u'UDF5', u'UDF6', u'UDF7', u'TaxArea', u'PriceLevel', u'DiscType', u'TrackRewards', u'CustomerID', u'WebNumber', u'WebFullNumber', u'EmailNotify', u'AR', u'UseAccCharge', u'AcceptChecks', u'DefaultShipTo', u'NoShipToBill', u'CreditLimit', u'DiscAllowed']

def get_remote_customer_chgs(seq):
	try:
		qb_client = get_qb_client()
		ret = qb_client.call_fn('get_cust_chg', {'last_id': seq})
	except:
		del_qb_client()
		raise

	return ret

def get_remote_customer(sid):
	try:
		qb_client = get_qb_client()
		ret = qb_client.call_fn('get_remote_customer', {'sid': sid})
	except:
		del_qb_client()
		raise

	return ret

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
		print ">CHG:", len(chg),
		n = _inst_sync_customer(cur, chg, lts)
		print "Done"
	set_remote_customer_inst_sync_last_id(cur[0], cur_last_id)
	if n == None: return
	print "DT: %s, LEN: %d, SECS: %0.3f" % (str(datetime.datetime.now()), n, time.time() - cts)

def _inst_sync_customer(cur, chg, lts):
	s_sids = ','.join([str(f_k) for f_k in chg.keys()])

	#test connection
	cur[1].execute('select 1')
	UNK = cur[1].fetchall()
	cur[0].execute('select 1')
	UNK = cur[0].fetchall()
	#

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


	new_cust = []
	cur[1].execute("select sid from customer where sid in (%s)" % (s_sids,))
	cur_sids = set([f_x[0] for f_x in cur[1].fetchall()])

	lst = []
	for sid,fchg in sorted(chg.items(), key=lambda f_x:f_x[0]):
		if sid not in cur_sids:
			r = get_remote_customer(sid)
			customer = r['customer'] = list(r['customer'])
			if customer[35]: continue

			customer[60] = 0.0
			customer[61] = 0.0
			customer[62] = 0.0
			customer[63] = 0.0
			customer[65] = 0

			lst.append( (0, sid, r) )
			continue

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
		if l: lst.append( (1, sid, l) )

	if not lst: return 0

	try:
		for mode,sid,flst in lst:
			if mode:
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
			else:
				r = flst
				cur[1].execute('insert into customer values(%s)' % (','.join('?' * len(r['customer'])), ), r['customer'])
				if r['customeraddress']:
					cur[1].executemany('insert into customeraddress values(%s)' % (','.join('?' * len(r['customeraddress'][0])), ), r['customeraddress'])
				if r['customerkeywords']:
					cur[1].executemany('insert into customerkeywords values(%s)' % (','.join('?' * len(r['customerkeywords'][0])), ), r['customerkeywords'])
				cur[1].execute("insert into changejournal values(default,'Customer',?,1,now(),'POSX', '-1')", (sid,))

		print "Committing...",
		cur[1].execute('commit')
		print "OK",

	except:
		cur[1].execute('rollback')
		raise

	return len(lst)


g_qb_client = None
def get_qb_client():
	global g_qb_client
	if g_qb_client == None: g_qb_client = QBClient()
	return g_qb_client

def del_qb_client():
	global g_qb_client
	g_qb_client = None


def main():
	qb_server = QBServer()
	qb_server.start_forever()

	srv_main( ((inst_sync_customer, 1000),) )

if __name__ == '__main__':
	main()
