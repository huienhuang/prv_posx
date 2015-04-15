import config
import datetime
import time
import cPickle
import json
import os
import db as mydb
import sys

mdb = mydb.db_mdb()
cur = mdb.cursor()

print "Looking For Phantom...", 
sids = set()
cur.execute('select GROUP_CONCAT(sid) from sync_items_hist group by itemsid,docsid having count(*) > 1')
for r in cur.fetchall(): sids.update( map(int, r[0].split(',')) )
print len(sids)
if not sids: sys.exit()


pdb= mydb.db_pos()
cur = pdb.cursor()

print "Looking For Items...",
itemsids = set()
cur.execute('select itemsid from Inventory where datastate=0')
for r in cur.fetchall(): itemsids.add(r[0])
print len(itemsids)


print "Checking...", 
eids = set()
l_sids = list(sids)
while l_sids:
	cur.execute('select historysid from InventoryHistory where historysid in (%s)' % (
		','.join(map(str, l_sids[:5000])),
		)
	)
	for r in cur.fetchall(): eids.add(r[0])
	l_sids = l_sids[5000:]

nids = sids - eids
print len(sids), len(eids), len(nids)
if not nids: sys.exit()


print 'Check Before Delete...',
dids = set()
cur = mdb.cursor()
cur.execute('select sid,itemsid from sync_items_hist where sid_type=0 and sid in (%s)' % (
	','.join(map(str, nids)),
	)
)
for r in cur.fetchall():
	if r[1] not in itemsids: continue
	dids.add(r[0])
print len(dids)
if not dids: sys.exit()


print 'Deleting...',
cur.execute('delete from sync_items_hist where sid_type=0 and sid in (%s)' % (
	','.join(map(str, dids)),
	)
)
print 'Done'


