import json
import time
import datetime
import config


CFG = {
	'id': 'SALEORDER_F5160821',
	'name': 'Sale Order',
	'perm_list': [
	('access', ''),
	]
}

class RequestHandler(App.load('/advancehandler').RequestHandler):

	def fn_item_barcode(self):
		self.req.writefile('mobile/item_barcode.html')

