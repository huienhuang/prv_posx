import config
import time
import datetime
import cPickle
import db
import sqlanydb

FS_DOC_TYPES = {'invoice': 2, 'creditmemo': 3, 'receivepayment': 4}

def sync_pos_links():
	sqlany_pos = {
	    'links': 'tcpip(host=10.0.0.70:55555;DoBroadcast=None)',
	    'ServerName': 's_qbpos',
	    'uid': 'spring',
	    'pwd': '852FB33855E2AD9386C918943AECFB'
	}
	dbc_0 = sqlanydb.connect(**sqlany_pos)
	cur_0 = dbc_0.cursor()

	dbc_1 = db.db_mdb()
	cur_1 = dbc_1.cursor()

	links = []
	cur_0.execute('select pos_sid,fs_id,fs_doctype from financialdetail where pos_doctype=5 order by sessionsid asc')
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

	print 'LINKS: %d, DT: %s' % (n, time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime()), )



sync_pos_links()

