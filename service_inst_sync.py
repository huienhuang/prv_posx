from service_base_v2 import srv_main
#import QBPOS
#import xml.etree.ElementTree as ET
import json
import time
import config
import cPickle
import urllib2
import base64
import hashlib
import gzip
import cStringIO

def gen_auth():
	ts_idx = int(int(time.time()) / 3600)

	pre_auth = hashlib.md5('%s%s%s%s' % (config.inst_sync_auth[1], config.secret_code, config.inst_sync_auth[0], config.inst_sync_auth[2])).digest()
	auth = hashlib.md5('%s%s%s' % (pre_auth, config.secret_code_v1, ts_idx)).hexdigest()

	return '%s:%s' % (config.inst_sync_auth[0], auth)

def get_remote_customer_chgs(seq):
	req = urllib2.Request('http://10.0.0.70/posx/sys?fn=get_cust_chg&last_id=%d' % (seq,))
	req.add_header('Accept-Encoding', 'gzip, deflate, sdch')
	req.add_header('Cookie', '__auth__="%s"' % (gen_auth(),))
	r = urllib2.urlopen(req)
	s = cStringIO.StringIO(r.read())
	r.close()

	z = gzip.GzipFile(fileobj=s)
	js = cPickle.loads(z.read())
	z.close()

	return js

def get_remote_customer_inst_sync_last_id():
	cur.execute('select cval from config where cid=%s', (cid__inst_sync_customer_last_id, ))
	rs = cur.fetchall()
	if rs:
		return int(rs[0][0])
	else:
		return dv

def inst_sync_customer(cur):
	last_id = get_remote_customer_inst_sync_last_id()
	chgs = get_remote_customer_chgs(last_id, 100)

	sids = set()
	mts = 0
	fts = {}
	for r in chgs:
		sids.add( str(r['sid']) )
		f = fts.setdefault(r['sid'], {})
		for i,v in r['js']:
			if f.has_key(i): continue
			f[i] = (v, r['ts'])

			if r['ts'] < mts: mts = r['ts']


	cur[0].execute("select * from sync_customer_chg from ts>=%s and ts<%s order by id desc", ())


	cs = {}
	cur[0].execute("select * from sync_customer_snapshots where sid in (%s)" % (','.join(sids), ))
	for r in cur[0].fetchall(): cs[ r[0] ] = (r[1], cPickle.loads(r[2]))

	upd_lst = []
	for sid,cts in sorted(fts.items(), key=lambda f_x:f_x[0]):
		s = cs.get(sid)
		if s == None: continue

		for k,v in cts.items():
			if v[1] > s[1]:
				pass
			else:
				pass



def main():
	srv_main( ((inst_sync_customer, 600),) )

if __name__ == '__main__':
    get_remote_customer_chgs(0)

