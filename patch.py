import config
import datetime
import time
import cPickle
import json
import os
import db as mydb

mdb = mydb.db_mdb()
cur = mdb.cursor()

cur.execute('select pid,rev,flg,pjs from inv_request where flg&2=0')
for r in cur.fetchall():
	pid,rev,flg,pjs = r

	pjs = json.loads(pjs)
	pjs = json.dumps({'items': pjs}, separators=(',',':'))
	cur.execute('update inv_request set rev=rev+1,flg=flg|2,pjs=%s where pid=%s', (pjs, pid,))


