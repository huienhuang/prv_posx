import config
import datetime
import time
import cPickle
import json
import os
import db as mydb
import sys

m_con = mydb.db_mdb()
m_cur = m_con.cursor()

pos_con = mydb.db_pos()
pos_cur = pos_con.cursor()


print "Looking For PO"
pos_cur.execute("select sid,datastate from PurchaseOrder")
g_po = dict(pos_cur.fetchall())


print "Checking PO..."
m_cur.execute("select sid,status from sync_purchaseorders")
for r in m_cur.fetchall():
	if r[1] >> 16: continue
	deleted = g_po.get(r[0], 1)
	if not deleted: continue
	m_cur.execute("update sync_purchaseorders set status=((1<<16)|(0xFFFF&status)) where sid=%d" % (r[0],))

print "Done"

