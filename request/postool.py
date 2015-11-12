import json
import time
import datetime
import config
import db


CFG = {
	'id': 'postool_C11E0017',
	'name': 'POS Tool',
	'perm_list': [
	('access', ''),
	]
}

class RequestHandler(App.load('/advancehandler').RequestHandler):

	def fn_item_barcode(self):
		self.req.writefile('mobile/item_barcode.html')


	def fn_save_info(self):
		js = self.req.psv_js('js')

		sid = int(js['sid'])
		units = [(str(v[0]), v[1] and int(v[1]) or None) for v in js['units']]
		vends = [(str(v[0]), v[1] and int(v[1]) or None) for v in js['vends']]

		cur = self.cur()
		js_s = json.dumps({'sid':sid, 'units':units, 'vends':vends}, separators=(',',':'))
		cur.execute('insert into qbpos values(null,1,1,-99,6,%s,%s,%s,%s)', (
			self.user_id, sid, 0, js_s
			)
		)

		self.req.writejs({'ret': 1})


