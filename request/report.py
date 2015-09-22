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
		{'id': 'salesrep', 'name': 'Sales Rep / AM', 'src': 'salesreport?fn=sale'},
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


	def fn_get_mom_sale(self):
		rjs = (self.get_data_file_cached('receipt_report', 'receipt_report.txt') or {}).get('summary', [])
		ms = rjs

		ym = []
		for mts,msa in ms:
			tp = time.localtime(mts)
			if not ym or ym[-1][0] != tp.tm_year: ym.append( (tp.tm_year, [0,] * 12) )
			m = ym[-1][1]
			m[tp.tm_mon - 1] += msa[1]

		self.req.writejs(ym)

	def fn_get_cate_sale(self):
		rjs = (self.get_data_file_cached('items_stat_v2', 'items_stat_v2.txt') or {}).get('types', {})

		self.req.writejs({'js': rjs})


	def fn_get_rep_sale(self):
		rjs = (self.get_data_file_cached('items_stat_v2', 'items_stat_v2.txt') or {}).get('clerks', {})

		self.req.writejs({'js': rjs})

