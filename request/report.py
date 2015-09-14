import json
import os
import time
import config
import re
import datetime


CFG = {
'id': 'REPORT_F1234567',
'name': 'Report',
'perm_list': [('access', ''),('admin', '')]
}


class RequestHandler(App.load('/advancehandler').RequestHandler):

	def fn_default(self):
		tabs = [
		{'id': 'dashboard', 'name': 'Dashboard'},
		{'id': 'reportgeneral', 'name': 'Operation KPI', 'singleview': 1},
		{'id': 'salesrep', 'name': 'Sales Rep / AM'},
		{'id': 'reportitem', 'name': 'Item Sale', 'singleview': 1},
		{'id': 'sreport', 'name': 'Customer Sale', 'src': 'sreport?fn=cust_by_dept'},
		]

		view = self.req.qsv_ustr('view')
		if view and view not in [ f_x['id'] for f_x in tabs ]: view = None
		if not view: view = tabs[0]['id']

		r = {
			'tab_cur_idx' : 2,
			'title': 'Report',
			'tabs': tabs,
			'view': view
		}
		self.req.writefile('tmpl_multitabs_bs_v1.html', r)


	def fn_dashboard(self):
		self.req.writefile('report/dashboard.html')