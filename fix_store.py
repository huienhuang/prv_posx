import config
import datetime
import time
import cPickle
import json
import os
import db as mydb
import sys
import json


pdb= mydb.db_pos()
cur = pdb.cursor()

cur.execute('select sid,store from receipt where datastate=0')
lst = list(cur.fetchall()) 


mdb = mydb.db_mdb()
cur = mdb.cursor()

for sid,store in lst:
	cur.execute('select global_js from sync_receipts where sid_type=0 and sid=%s', (sid,))
	js = json.loads(cur.fetchall()[0][0])
	js['store'] = store

	cur.execute('update sync_receipts set global_js=%s where sid_type=0 and sid=%s', (
		json.dumps(js, separators=(',',':')), sid,
		)
	)

