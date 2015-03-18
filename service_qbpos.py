from service_base_v2 import srv_main, open_db
import QBPOS
import xml.etree.ElementTree as ET
import json
import time
import config


g_cfg = config.qbpos_cfg


def rf(s, n=0): return config.round_ex(float(s), n)
def rf2(s): return rf(s, 2)

__g_pos_conn = None
def get_pos_conn():
	global __g_pos_conn
	if __g_pos_conn == None:
		__g_pos_conn = QBPOS.OpenConnection(g_cfg["computer"], g_cfg["company"], "8")

	return __g_pos_conn

def del_pos_conn():
	global __g_pos_conn
	__g_pos_conn = None


def pos_process_request(c, s):
	try:
		return QBPOS.ProcessRequest(c, s)
	except:
		del_pos_conn()
		raise

def insert_transfer_slip(cur, r):
	cur[0].execute("select t.*,u.user_name from inv_request t left join user u on (t.uid=u.user_id) where pid=%s and qbpos_id=%s", (r['doc_id'], r["id"]))
	rr = cur[0].fetchall()
	if not rr: return (-1, None, 'Transfer Slip Not Found')
	rr = dict(zip(cur[0].column_names, rr[0]))

	lst = json.loads(rr['pjs'])['items']
	if not lst: return (-1, None, 'No Items')
	cur[0].execute("select sid,detail from sync_items where sid in (%s)" % ','.join([str(f_x[0]) for f_x in lst]))
	items = {}
	for a in cur[0].fetchall(): items[ a[0] ] = json.loads(a[1])
	
	tree = ET.fromstring('<QBPOSXML><QBPOSXMLMsgsRq onError="stopOnError"><TransferSlipAddRq><TransferSlipAdd></TransferSlipAdd></TransferSlipAddRq></QBPOSXMLMsgsRq></QBPOSXML>')
	T_TransferSlipAdd = tree.find('QBPOSXMLMsgsRq/TransferSlipAddRq/TransferSlipAdd')

	T_ELEM = ET.Element('Associate')
	T_ELEM.text = rr['user_name']
	T_TransferSlipAdd.append(T_ELEM)

	T_ELEM = ET.Element('Comments')
	T_ELEM.text = "AutoGen From POSX TS#%d - %s" % (r['doc_id'], time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime()))
	T_TransferSlipAdd.append(T_ELEM)

	if rr['dst']:
		T_ELEM = ET.Element('FromStoreNumber')
		T_ELEM.text = "2"
		T_TransferSlipAdd.append(T_ELEM)

		T_ELEM = ET.Element('ToStoreNumber')
		T_ELEM.text = "1"
		T_TransferSlipAdd.append(T_ELEM)
	else:
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
	xml = pos_process_request(pos_conn, xml.decode('utf8'))
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

def insert_po(cur, r):
	cur[0].execute("select t.*,u.user_name from inv_request t left join user u on (t.uid=u.user_id) where pid=%s and qbpos_id=%s", (r['doc_id'], r["id"]))
	rr = cur[0].fetchall()
	if not rr: return (-1, None, 'PO Not Found')
	rr = dict(zip(cur[0].column_names, rr[0]))

	lst = json.loads(rr['pjs'])['items']
	if not lst: return (-1, None, 'No Items')
	cur[0].execute("select sid,detail from sync_items where sid in (%s)" % ','.join([str(f_x[0]) for f_x in lst]))
	items = {}
	for a in cur[0].fetchall(): items[ a[0] ] = json.loads(a[1])
	
	tree = ET.fromstring('<QBPOSXML><QBPOSXMLMsgsRq onError="stopOnError"><PurchaseOrderAddRq><PurchaseOrderAdd></PurchaseOrderAdd></PurchaseOrderAddRq></QBPOSXMLMsgsRq></QBPOSXML>')
	T_PurchaseOrderAdd = tree.find('QBPOSXMLMsgsRq/PurchaseOrderAddRq/PurchaseOrderAdd')

	T_ELEM = ET.Element('Associate')
	T_ELEM.text = rr['user_name']
	T_PurchaseOrderAdd.append(T_ELEM)

	T_ELEM = ET.Element('VendorListID')
	T_ELEM.text = '1000000002'
	T_PurchaseOrderAdd.append(T_ELEM)

	T_ELEM = ET.Element('Instructions')
	T_ELEM.text = "AutoGen From POSX PO#%d - %s" % (r['doc_id'], time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime()))
	T_PurchaseOrderAdd.append(T_ELEM)

	T_ELEM = ET.Element('StoreNumber')
	T_ELEM.text = '1'
	T_PurchaseOrderAdd.append(T_ELEM)

	if rr['dst']:
		T_ELEM = ET.Element('ShipToStoreNumber')
		T_ELEM.text = '1'
		T_PurchaseOrderAdd.append(T_ELEM)
	else:
		T_ELEM = ET.Element('ShipToStoreNumber')
		T_ELEM.text = '2'
		T_PurchaseOrderAdd.append(T_ELEM)

	for a in lst:
		item = items.get(a[0])
		if not item: return (-1, None, 'Item %d No Found' % (a[1],))
		units = item['units']
		if a[2] >= len(units): return (-1, None, 'Item %d UOM Not Found' % (a[1],))
		uom = units[ a[2] ][2]

		T_PurchaseOrderItemAdd = ET.Element('PurchaseOrderItemAdd')

		T_ELEM = ET.Element('ListID')
		T_ELEM.text = str(a[0])
		T_PurchaseOrderItemAdd.append(T_ELEM)

		T_ELEM = ET.Element('Qty')
		T_ELEM.text = str(a[3])
		T_PurchaseOrderItemAdd.append(T_ELEM)

		if uom:
			T_ELEM = ET.Element('UnitOfMeasure')
			T_ELEM.text = uom
			T_PurchaseOrderItemAdd.append(T_ELEM)

		T_PurchaseOrderAdd.append(T_PurchaseOrderItemAdd)

	xml = '<?xml version="1.0" ?><?qbposxml version="3.0"?>' + ET.tostring(tree, 'utf8')
	pos_conn = get_pos_conn()
	xml = pos_process_request(pos_conn, xml.decode('utf8'))
	if not xml: return (-111, None, 'QBPOS Runtime Error')
	tree = ET.fromstring(xml)

	rs = tree.find("QBPOSXMLMsgsRs/PurchaseOrderAddRs")
	msg = (rs.get('statusSeverity') + ' ' + rs.get('statusMessage', '')).strip()

	if int(rs.get('statusCode')) != 0:
		return (-2, None, msg)
	else:
		rt = rs.find('PurchaseOrderRet')
		sid = int(rt.find('TxnID').text)
		num = int(rt.find('PurchaseOrderNumber').text)
		return (0, (sid, num), msg)


def disc_v(v, percent):
	return rf2(v * (100.0 + percent) / 100.0)

def validate(cur, r, req, ijs):
	cur[1].execute("select * from PurchaseOrder where datastate=0 and sid=?", (req['ref'],))
	row = cur[1].fetchall()
	if not row: return (-1, None, 'PO Not Found')
	cnz = [ d[0].lower() for d in cur[1].description ]
	po = dict(zip(cnz, row[0]))

	items = po['items'] = []
	cur[1].execute('select * from PurchaseOrderItem where sid=? order by itempos asc', (req['ref'],))
	cnz = [ d[0].lower() for d in cur[1].description ]
	for row in cur[1].fetchall(): items.append( dict(zip(cnz, row)) )
	if len(ijs) != len(items): return (-2, None, 'Items LEN Not Match')

	units = {}
	sids = ','.join(set([ str(f_x['itemsid']) for f_x in items]))
	cur[1].execute('select itemsid,price1,price2,price3,price4,price5,price6,unitofmeasure from inventory where datastate=0 and itemsid in (%s)' % (sids,))
	for row in cur[1].fetchall(): units.setdefault(row[0], []).append( list(map(rf2, row[1:7])) + [1, (row[7] or '').lower(), 0] )

	if len(units) != len(ijs): return (-2, None, 'Items LEN Not Match')

	cur[1].execute('select itemsid,price1,price2,price3,price4,price5,price6,unitfactor,unitofmeasure,uompos from inventoryunits where itemsid in (%s) order by uompos asc' % (sids,))
	for row in cur[1].fetchall(): units.setdefault(row[0], []).append( list(map(rf2, row[1:8])) + [(row[8] or '').lower(), row[9] + 1] )

	errs = []
	for i in range(len(items)):
		r = ijs[i]
		e = items[i]
		if r['sid'] != e['itemsid']:
			errs.append('#%d - Sid Not Matched' % (i + 1, ))
			continue
		if r['cost'] != rf2(e['cost']):
			errs.append('#%d - Cost Not Matched' % (i + 1, ))
			continue
		if r['units'] != units.get(r['sid']):
			errs.append('#%d - Price Or Unit Not Matched' % (i + 1, ))
			continue

	if errs: return (-3, None, '\n'.join(errs))

	return (0, (po, items, units))


def adjust_po(cur, r):
	posr = r
	cur[0].execute("select t.*,u.user_name from inv_request t left join user u on (t.uid=u.user_id) where pid=%s and qbpos_id=%s", (r['doc_id'], r["id"]))
	row = cur[0].fetchall()
	if not row: return (-1, None, 'PO REQ Not Found')
	req = dict(zip(cur[0].column_names, row[0]))
	pjs = req['pjs'] = json.loads(req['pjs'])
	ijs = pjs['ijs']

	ret = validate(cur, posr, req, ijs)
	if ret[0] != 0: return ret
	po,items,units = ret[1]

	p_po_flg = [0,] * len(items)
	p_it_flg = [0,] * len(items)
	new_ijs = []
	for i in range(len(items)):
		r = ijs[i]
		e = items[i]
		nr = r.copy()
		new_ijs.append(nr)

		if r['new_cost'] != rf2(e['cost']):
			p_po_flg[i] = 1
			nr['cost'] = round(r['new_cost'], 2)

		if r['new_diff']:
			p_it_flg[i] = 1
			new_units = nr['units'] = []
			for u in r['units']:
				nu = u[:]
				new_units.append(nu)
				for j in range(6): nu[j] = disc_v(u[j], r['new_diff'])

	msgs = []

	if any(p_po_flg):
		tree = ET.fromstring('<QBPOSXML><QBPOSXMLMsgsRq onError="stopOnError"><PurchaseOrderModRq><PurchaseOrderMod></PurchaseOrderMod></PurchaseOrderModRq></QBPOSXMLMsgsRq></QBPOSXML>')
		T_ROOT = tree.find('QBPOSXMLMsgsRq/PurchaseOrderModRq/PurchaseOrderMod')

		T_ELEM = ET.Element('TxnID')
		T_ELEM.text = str(req['ref'])
		T_ROOT.append(T_ELEM)

		T_ELEM = ET.Element('Instructions')
		T_ELEM.text = ', '.join([(po['comments'] or ''), 'POSX Adjusted(#%s) - %s' % (req['pid'], time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime()))])
		T_ROOT.append(T_ELEM)

		for i in range(len(new_ijs)):
			r = new_ijs[i]
			T_GROUP = ET.Element('PurchaseOrderItemMod')
			T_ROOT.append(T_GROUP)

			T_ELEM = ET.Element('TxnLineID')
			T_ELEM.text = str(i + 1)
			T_GROUP.append(T_ELEM)

			if p_po_flg[i]:
				T_ELEM = ET.Element('Cost')
				T_ELEM.text = "%0.2f" % (r['cost'], )
				T_GROUP.append(T_ELEM)

		xml = '<?xml version="1.0" ?><?qbposxml version="3.0"?>' + ET.tostring(tree, 'utf8')
		pos_conn = get_pos_conn()
		xml = pos_process_request(pos_conn, xml.decode('utf8'))
		if not xml: return (-111, None, 'QBPOS Runtime Error')
		tree = ET.fromstring(xml)

		rs = tree.find("QBPOSXMLMsgsRs/PurchaseOrderModRs")
		msg = ('#0 - ' + rs.get('statusSeverity') + ' ' + rs.get('statusMessage', '')).strip()
		if int(rs.get('statusCode')) != 0: return (-2, None, msg)
		msgs.append(msg)

	errc = 0
	if any(p_it_flg):
		for i in range(len(new_ijs)):
			r = new_ijs[i]
			if not p_it_flg[i]:
				msgs.append('#' + str(i + 1) + ' - SKIP')
				continue

			tree = ET.fromstring('<QBPOSXML><QBPOSXMLMsgsRq onError="stopOnError"><ItemInventoryModRq><ItemInventoryMod></ItemInventoryMod></ItemInventoryModRq></QBPOSXMLMsgsRq></QBPOSXML>')
			T_ROOT = tree.find('QBPOSXMLMsgsRq/ItemInventoryModRq/ItemInventoryMod')

			T_ELEM = ET.Element('ListID')
			T_ELEM.text = str(r['sid'])
			T_ROOT.append(T_ELEM)

			u = r['units'][0]
			for j in range(5):
				T_ELEM = ET.Element('Price' + str(j + 1))
				T_ELEM.text = '%0.2f' % (u[j], )
				T_ROOT.append(T_ELEM)

			k = 1
			for u in r['units'][k:]:
				T_GROUP = ET.Element('UnitOfMeasure' + str(k))
				T_ROOT.append(T_GROUP)
				for j in range(5):
					T_ELEM = ET.Element('Price' + str(j + 1))
					T_ELEM.text = '%0.2f' % (u[j], )
					T_GROUP.append(T_ELEM)

			xml = '<?xml version="1.0" ?><?qbposxml version="3.0"?>' + ET.tostring(tree, 'utf8')
			pos_conn = get_pos_conn()
			xml = pos_process_request(pos_conn, xml.decode('utf8'))
			if not xml: return (-111, None, 'QBPOS Runtime Error')
			tree = ET.fromstring(xml)

			rs = tree.find("QBPOSXMLMsgsRs/ItemInventoryModRs")
			msg = ('#' + str(i + 1) + ' - ' + rs.get('statusSeverity') + ' ' + rs.get('statusMessage', '')).strip()

			if int(rs.get('statusCode')) != 0: errc += 1
			msgs.append(msg)

	ret = validate(cur, posr, req, new_ijs)
	if ret[0]:
		errc += 1
		msgs.append(ret[2])

	return (errc != 0 and -9 or 0, (None, 0), '\n'.join(msgs))

def worker(cur):
	ts = time.time()
	rs = []

	cur[0].execute("select * from qbpos where state = 1 limit 10")
	nz = cur[0].column_names
	for r in cur[0].fetchall():
		r = dict(zip(nz, r))

		if r['doc_type'] == 1:
			ret = insert_transfer_slip(cur, r)
		elif r['doc_type'] == 2:
			ret = insert_po(cur, r)
		elif r['doc_type'] == 3:
			ret = adjust_po(cur, r)
		else:
			ret = (-1, None, 'Invalid Type')

		errno,doc_info,doc_msg = ret
		if errno == -111:
			del_pos_conn()
		else:
			if not errno:
				cur[0].execute("update qbpos set rev=rev+1,state=%s,errno=%s,doc_sid=%s,doc_num=%s,js=%s where id=%s and state=1", (
					2, errno, doc_info[0], doc_info[1], json.dumps({'msg':doc_msg}, separators=(',',':')), r['id'],
					)
				)
			else:
				cur[0].execute("update qbpos set rev=rev+1,state=%s,errno=%s,js=%s where id=%s and state=1", (
					2, errno, json.dumps({'msg':doc_msg}, separators=(',',':')), r['id'],
					)
				)

		rs.append( (r, ret) )

	secs = time.time() - ts
	if rs:
		print "+>%s" % (time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime()), )
		for r,ret in rs:
			print "-- %s > %s" % (r['id'], ret)
		print '->%0.3fs' % (secs,)

def main():
	#get_pos_conn()
	srv_main( ((worker, 600),) )

if __name__ == '__main__':
    main()

    
    #dbs = {}
    #cur = (open_db(dbs, 'mysql')[1], open_db(dbs, 'sqlany')[1])
    #cur[0].execute("select * from qbpos where state = 1 and doc_type=3 limit 10")
    #r = dict(zip(cur[0].column_names, cur[0].fetchall()[0]))

    #print adjust_po(cur, r)
    