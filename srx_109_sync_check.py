import config
import datetime
import time
import cPickle
import json
import os
import db as mydb
import math
import sys
import TinyServer


def ri(s): return int(math.floor(float(s)))
def rf(s, n=0): return config.round_ex(float(s), n)
def rf2(s): return rf(s, 2)


print 'Comparing POS AND POSX'

g_items = {}

pdb= mydb.db_pos()
cur = pdb.cursor()
cur.execute('select * from inventory where datastate=0')
col_nzs = [ d[0].lower() for d in cur.description ]
for r in cur.rows():
	r = dict(zip(col_nzs, r))

	units = []
	units.append([
		[ rf2(r['price1']), rf2(r['price2']), rf2(r['price3']), rf2(r['price4']), rf2(r['price5']), rf2(r['price6']) ],
		r['alu'] or '', r['unitofmeasure'] or '', 1, r['upc'] and str(r['upc']) or ''
	])

	g_items[ r['itemsid'] ] = units


cur.execute('select * from inventoryunits order by uompos asc')
col_nzs = [ d[0].lower() for d in cur.description ]
for r in cur.rows():
	r = dict(zip(col_nzs, r))

	u = [
		[ rf2(r['price1']), rf2(r['price2']), rf2(r['price3']), rf2(r['price4']), rf2(r['price5']), rf2(r['price6']) ],
		r['alu'] or '', r['unitofmeasure'] or '', rf2(r['unitfactor']), r['upc'] and str(r['upc']) or ''
	]

	g_items.get(r['itemsid'], []).append(u)




g_items_2 = {}

mdb = mydb.db_mdb()
cur = mdb.cursor()
cur.execute('select sid,detail from sync_items')
for r in cur: g_items_2[ r[0] ] = json.loads(r[1])['units']


for sid,units in g_items.items():
	units_2 = g_items_2.get(sid)
	if units != units_2:
		print sid, units, units_2


if not config.inst_sync_cfg.get('master'): sys.exit()




class QBClient(TinyServer.TinyAsyncMsgClient):
	def __init__(self):
		TinyServer.TinyAsyncMsgClient.__init__(self, config.inst_sync_cfg['remote'])

	def call_fn(self, fn, arg):
		p = cPickle.dumps({'fn': fn, 'arg': arg, 'auth': config.inst_sync_cfg['auth']}, 1)
		self.send_packet(zlib.compress(p, 9))

		p = zlib.decompress( self.recv_packet() )
		return cPickle.loads(p)['ret']


print " <--> "
print 'Comparing HQ AND STORE'

g_items_2 = QBClient().call_fn('get_item_units', {})

for sid,units in g_items.items():
	units_2 = g_items_2.get(sid)
	if units != units_2:
		print sid, units, units_2


