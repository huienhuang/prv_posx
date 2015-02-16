from service_base import srv_main
import QBPOS
import xml.etree.ElementTree as ET
import json
import time

g_cfg = {
"computer" : "devhq",
"company" : "forest_hq"
}


__g_pos_conn = None
def get_pos_conn():
	global __g_pos_conn
	if __g_pos_conn == None:
		__g_pos_conn = QBPOS.OpenConnection(g_cfg["computer"], g_cfg["company"], "8")

	return __g_pos_conn

def del_pos_conn():
	global __g_pos_conn
	__g_pos_conn = None


def insert_transfer_slip(cur, r):
	cur.execute("select t.*,u.user_name from transferslip t left join user u on (t.uid=u.user_id) where pid=%s and qbpos_id=%s", (r['doc_id'], r["id"]))
	rr = cur.fetchall()
	if not rr: return (-1, None, 'Transfer Slip Not Found')
	rr = dict(zip(cur.column_names, rr[0]))

	lst = json.loads(rr['pjs'])
	if not lst: return (-1, None, 'No Items')
	cur.execute("select sid,detail from sync_items where sid in (%s)" % ','.join([str(f_x[0]) for f_x in lst]))
	items = {}
	for a in cur.fetchall(): items[ a[0] ] = json.loads(a[1])
	
	tree = ET.fromstring('<QBPOSXML><QBPOSXMLMsgsRq onError="stopOnError"><TransferSlipAddRq><TransferSlipAdd></TransferSlipAdd></TransferSlipAddRq></QBPOSXMLMsgsRq></QBPOSXML>')
	T_TransferSlipAdd = tree.find('QBPOSXMLMsgsRq/TransferSlipAddRq/TransferSlipAdd')

	T_ELEM = ET.Element('Associate')
	T_ELEM.text = rr['user_name']
	T_TransferSlipAdd.append(T_ELEM)

	T_ELEM = ET.Element('Comments')
	T_ELEM.text = "AutoGen From POSX TS#%d - %s" % (r['doc_id'], time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime()))
	T_TransferSlipAdd.append(T_ELEM)

	T_ELEM = ET.Element('FromStoreNumber')
	T_ELEM.text = "1"
	T_TransferSlipAdd.append(T_ELEM)

	T_ELEM = ET.Element('ToStoreNumber')
	T_ELEM.text = "2"
	T_TransferSlipAdd.append(T_ELEM)

	T_ELEM = ET.Element('TxnState')
	T_ELEM.text = "Normal"
	T_TransferSlipAdd.append(T_ELEM)

	for a in lst:
		item = items.get(a[0])
		if not item: return (-1, None, 'Item %d No Found' % (a[1],))
		units = item['units']
		if a[2] >= len(units): return (-1, None, 'Item %d UOM Not Found' % (a[1],))
		uom = units[ a[2] ][2]

		TransferSlipItemAdd = ET.Element('TransferSlipItemAdd')

		T_ELEM = ET.Element('ListID')
		T_ELEM.text = str(a[0])
		TransferSlipItemAdd.append(T_ELEM)

		T_ELEM = ET.Element('Qty')
		T_ELEM.text = str(a[3])
		TransferSlipItemAdd.append(T_ELEM)

		if uom:
			T_ELEM = ET.Element('UnitOfMeasure')
			T_ELEM.text = uom
			TransferSlipItemAdd.append(T_ELEM)

		T_TransferSlipAdd.append(TransferSlipItemAdd)

	xml = '<?xml version="1.0" ?><?qbposxml version="3.0"?>' + ET.tostring(tree, 'utf8')
	pos_conn = get_pos_conn()
	xml = QBPOS.ProcessRequest(pos_conn, xml.decode('utf8'))
	if not xml: return (-111, None, 'QBPOS Runtime Error')
	tree = ET.fromstring(xml)

	rs = tree.find("QBPOSXMLMsgsRs/TransferSlipAddRs")
	msg = (rs.get('statusSeverity') + ' ' + rs.get('statusMessage', '')).strip()

	if int(rs.get('statusCode')) != 0:
		return (-2, None, msg)
	else:
		rt = rs.find('TransferSlipRet')
		sid = int(rt.find('TxnID').text)
		num = int(rt.find('SlipNumber').text)
		return (0, (sid, num), msg)

def worker(cur):

	cur.execute("select * from qbpos where state = 1 limit 10")
	nz = cur.column_names
	for r in cur.fetchall():
		r = dict(zip(nz, r))

		if r['doc_type'] == 1:
			ret = insert_transfer_slip(cur, r)

		errno,doc_info,doc_msg = ret
		if errno == -111:
			del_pos_conn()
		else:
			cur.execute("update qbpos set rev=rev+1,state=%s,errno=%s,doc_sid=%s,doc_num=%s,js=%s where id=%s and state=1", (
				2, errno, doc_info[0], doc_info[1], json.dumps({'msg':doc_msg}, separators=(',',':')), r['id'],
				)
			)

import mysql.connector as MySQL
import config

conn = MySQL.connect(**config.mysql)
cur = conn.cursor()

print worker(cur)

