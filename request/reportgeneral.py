import json
import os
import time
import config
import re
import datetime


PERM_ADMIN = 1 << config.USER_PERM_BIT['admin']

G_MAP_REPORTS = [
    ('AR Ages', PERM_ADMIN, 'ar_ages'),
    ('Active Customers', PERM_ADMIN, 'active_customers'),
    ('Customer Retention Rate', PERM_ADMIN, 'customer_retention_rate'),
    ('Average Order Value', PERM_ADMIN, 'average_order_value'),
    ('Delivery Perfect Order', PERM_ADMIN, 'delivery_perfect_order'),
]


DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        reports = []
        for i in range(len(G_MAP_REPORTS)):
            report = G_MAP_REPORTS[i]
            if not(self.user_lvl & report[1]): continue
            reports.append( (i, report[0]) )
        
        self.req.writefile('report_general.html', {'reports': reports})
        
        
    def fn_get_report(self):
        report_idx = self.qsv_int('idx')
        if report_idx < 0 or report_idx >= len(G_MAP_REPORTS): return
        
        report = G_MAP_REPORTS[report_idx]
        if not(self.user_lvl & report[1]): return
        
        getattr(self, 'report_%s' % (report[2], ))()
    
    
    def report_average_order_value(self):
        js = self.get_data_file_cached('receipt_report', 'receipt_report.txt')
        if not js: return
        
        dps = []
        for k,v in js['summary']: dps.append( {'x': k * 1000, 'y': round(v[1] / float(v[0] or 1), 2), 'count': v[0]} );
        
        chart_config = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "Average Order Value"},
            'axisX': {'valueFormatString': "MMM-YYYY", 'labelAngle': -50},
            'data': [
                {'toolTipContent': '{x}: {y}, Count: {count}', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps}
            ]
        }
        self.req.writejs({'type':'chart', 'config': chart_config})
    
    def report_active_customers(self):
        cr = self.get_customer_report()
        if not cr: return
                
        dps = []
        for k,v in cr['active_counts']: dps.append( {'x': k * 1000, 'y': v} );
                
        chart_config = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "Active Customers"},
            'axisX': {'valueFormatString': "MMM-YYYY", 'labelAngle': -50},
            'data': [ {'type': "line", 'xValueType': "dateTime", 'dataPoints': dps} ]
        }
        self.req.writejs({'type':'chart', 'config': chart_config})
        
    def report_ar_ages(self):
        js = self.get_data_file_cached('qb_ar_dues', 'qb_ar_dues.txt')
        if not js: return
        
        dps_0 = []
        dps_1 = []
        dps_2 = []
        dps_3 = []
        for k,v in js['dues']:
            b = float(v[-1] or 1)
            dps_0.append({'x': k * 1000, 'y': round(v[0] / b, 2)})
            dps_1.append({'x': k * 1000, 'y': round(v[1] / b, 2)})
            dps_2.append({'x': k * 1000, 'y': round(v[2] / b, 2)})
            dps_3.append({'x': k * 1000, 'y': round(v[3] / b, 2)})
        
        chart_config = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "AR Ages"},
            'axisX': {'valueFormatString': "MMM-YYYY", 'labelAngle': -50},
            'data': [
                {'showInLegend': True, 'type': "line", 'xValueType': "dateTime", 'name': '<=30', 'dataPoints': dps_0},
                {'showInLegend': True, 'type': "line", 'xValueType': "dateTime", 'name': '<=60', 'dataPoints': dps_1},
                {'showInLegend': True, 'type': "line", 'xValueType': "dateTime", 'name': '<=90', 'dataPoints': dps_2},
                {'showInLegend': True, 'type': "line", 'xValueType': "dateTime", 'name': '90+', 'dataPoints': dps_3},
            ]
        }
        
        self.req.writejs({'type':'chart', 'config': chart_config})


    def report_customer_retention_rate(self):
        js = self.get_data_file_cached('customer_report', 'customer_report.txt')
        if not js: return
        
    def report_delivery_perfect_order(self):
        js = self.get_data_file_cached('delivery_report', 'delivery_report.txt')
        if not js: return
        
        dps = []
        for k,v in js['mons']: dps.append( {'x': k * 1000, 'y': round(v['perfect'] / float(len(v['nums']) or 1), 2), 'count': len(v['nums'])} );
        
        chart_config = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "Average Order Value"},
            'axisX': {'valueFormatString': "MMM-YYYY", 'labelAngle': -50},
            'data': [
                {'toolTipContent': '{x}: {y}, Count: {count}', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps}
            ]
        }
        self.req.writejs({'type':'chart', 'config': chart_config})
        
        
        
        

