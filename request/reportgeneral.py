import json
import os
import time
import config
import re
import datetime
import cStringIO
import csv


PERM_ADMIN = 1 << config.USER_PERM_BIT['admin']

G_MAP_REPORTS = [
    ('AR Ages', PERM_ADMIN, 'ar_ages'),
    ('Active Customers', PERM_ADMIN, 'active_customers'),
    ('Average Order Value', PERM_ADMIN, 'average_order_value'),
    ('Delivery Perfect Order', PERM_ADMIN, 'delivery_perfect_order'),
    ('Worker Productivity', PERM_ADMIN, 'worker_productivity'),
    ('Inventory To Sales Ratio', PERM_ADMIN, 'inventory_to_sales_ratio'),
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
        frm_ts = to_ts = 0
        dt = self.qsv_str('frm')
        if dt: frm_ts = int(time.mktime(time.strptime(dt, "%Y-%m")))
        dt = self.qsv_str('to')
        if dt: to_ts = int(time.mktime(time.strptime(dt, "%Y-%m")))
        
        report_idx = self.qsv_int('idx')
        if report_idx < 0 or report_idx >= len(G_MAP_REPORTS): return
        
        report = G_MAP_REPORTS[report_idx]
        if not(self.user_lvl & report[1]): return
        
        js = getattr(self, 'report_%s' % (report[2], ))(frm_ts, to_ts)
        self.req.writejs(js)
    
    def fn_get_reports(self):
        frm_ts = to_ts = 0
        dt = self.qsv_str('frm')
        if dt: frm_ts = int(time.mktime(time.strptime(dt, "%Y-%m")))
        dt = self.qsv_str('to')
        if dt: to_ts = int(time.mktime(time.strptime(dt, "%Y-%m")))
        
        lst = []
        for report in G_MAP_REPORTS:
            if not(self.user_lvl & report[1]): continue
            js = getattr(self, 'report_%s' % (report[2], ))(frm_ts, to_ts)
            lst.append(js)
        self.req.writejs(lst)
    
    def report_average_order_value(self, frm_ts, to_ts):
        js = self.get_data_file_cached('receipt_report', 'receipt_report.txt')
        if not js: return
        
        dps = []
        dps_1 = []
        for k,v in js['summary']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            if not v[0]: continue
            dps.append( {'x': k * 1000, 'y': round(v[1] / float(v[0]), 2), 'count': v[0]} );
            dps_1.append( {'x': k * 1000, 'y': v[0]} );
        
        chart_config = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "Receipts"},
            'axisY': {'title':"Average"},
            'axisY2': {'title':"Count"},
            'axisX': {'valueFormatString': "MMM-YYYY", 'labelAngle': -50},
            'data': [
                {'showInLegend': True, 'name': 'Average', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps},
                {'showInLegend': True, 'name': 'Count', 'axisYType': 'secondary', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps_1}
            ]
        }
        return {'type':'chart', 'config': chart_config}
    
    def export_report_average_order_value(self, frm_ts, to_ts):
        js = self.get_data_file_cached('receipt_report', 'receipt_report.txt')
        if not js: return
        
        lst = []
        for k,v in js['summary']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            if not v[0]: continue
            lst.append( (k, round(v[1] / float(v[0]), 2), v[0]) )
            
        return (('AvgPerOrder', 'TotalOrdersCount'), lst)
    
    def export_report_ar_ages(self, frm_ts, to_ts):
        js = self.get_data_file_cached('qb_ar_dues', 'qb_ar_dues.txt')
        if not js: return
        
        lst = []
        for k,v in js['dues']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            if not v[-1]: continue
            b = float(v[-1]) / 100
            lst.append( (k, round(v[0] / b, 2), round(v[1] / b, 2), round(v[2] / b, 2), round(v[3] / b, 2)) )
        
        return (('<=30', '<=60', '<=90', '90+'), lst)


    def report_ar_ages(self, frm_ts, to_ts):
        js = self.get_data_file_cached('qb_ar_dues', 'qb_ar_dues.txt')
        if not js: return
        
        dps_0 = []
        dps_1 = []
        dps_2 = []
        dps_3 = []
        for k,v in js['dues']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            if not v[-1]: continue
            b = float(v[-1]) / 100
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
        
        return {'type':'chart', 'config': chart_config}


    def report_active_customers(self, frm_ts, to_ts):
        js = self.get_data_file_cached('customer_report', 'customer_report.txt')
        if not js: return
        
        dps_0 = []
        dps_1 = []
        for k,v in js['retention_rate']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            if not v[0]: continue
            b = float(v[0]) / 100
            r = round(v[1] / b, 2)
            if r >= 1000: continue
            dps_0.append({'x': k * 1000, 'y': r})
            dps_1.append({'x': k * 1000, 'y': round(v[2] / b, 2)})
        
        dps_2 = []
        for k,v in js['active_counts']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            dps_2.append( {'x': k * 1000, 'y': v} );
        
        chart_config = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "Active Customers"},
            'axisX': {'valueFormatString': "MMM-YYYY", 'labelAngle': -50},
            'axisY': {'title':"Retention Rate"},
            'axisY2': {'title':"Active Count"},
            'data': [
                {'showInLegend': True, 'type': "line", 'xValueType': "dateTime", 'name': 'New+Old', 'dataPoints': dps_0},
                {'showInLegend': True, 'type': "line", 'xValueType': "dateTime", 'name': 'Old Only', 'dataPoints': dps_1},
                {'axisYType': 'secondary', 'showInLegend': True, 'type': "line", 'xValueType': "dateTime", 'name': 'Active Customers', 'dataPoints': dps_2},
            ]
        }
        
        return {'type':'chart', 'config': chart_config}
    
    def export_report_active_customers(self, frm_ts, to_ts):
        js = self.get_data_file_cached('customer_report', 'customer_report.txt')
        if not js: return
        
        frm_tp = time.localtime(frm_ts)
        to_tp = time.localtime(to_ts)
        min_d = frm_tp.tm_year * 12 + frm_tp.tm_mon
        max_d = to_tp.tm_year * 12 + to_tp.tm_mon
        
        lst = []
        for i in range(min_d, max_d + 1): lst.append( [None, None, None, None] )
        for k,v in js['retention_rate']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            if not v[0]: continue
            b = float(v[0]) / 100
            r = round(v[1] / b, 2)
            if r >= 1000: continue
            
            cur_tp = time.localtime(k)
            l = lst[ cur_tp.tm_year * 12 + cur_tp.tm_mon - min_d ]
            l[0] = k
            l[1] = r
            l[2] = round(v[2] / b, 2)
        
        for k,v in js['active_counts']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            
            cur_tp = time.localtime(k)
            l = lst[ cur_tp.tm_year * 12 + cur_tp.tm_mon - min_d ]
            l[0] = k
            l[3] = v
            
        return (('New+Old', 'Old Only', 'ActiveCount'), lst)
        
        
    def export_report_delivery_perfect_order(self, frm_ts, to_ts):
        js = self.get_data_file_cached('delivery_report', 'delivery_report.txt')
        if not js: return
        
        lst = []
        for k,v in js['mons']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            if not len(v['nums']): continue
            lst.append( (k, round(v['perfect'] * 100 / float(len(v['nums'])), 2)) )
        
        return (('PerfectRate',), lst)
    
    def report_delivery_perfect_order(self, frm_ts, to_ts):
        js = self.get_data_file_cached('delivery_report', 'delivery_report.txt')
        if not js: return
        
        dps = []
        for k,v in js['mons']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            if not len(v['nums']): continue
            dps.append( {'x': k * 1000, 'y': round(v['perfect'] * 100 / float(len(v['nums'])), 2), 'count': len(v['nums'])} );
        
        chart_config = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "Delivery Perfect Order"},
            'axisX': {'valueFormatString': "MMM-YYYY", 'labelAngle': -50},
            'data': [
                {'toolTipContent': '{x}: {y}, Count: {count}', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps}
            ]
        }
        return {'type':'chart', 'config': chart_config} 
        
    def export_report_worker_productivity(self, frm_ts, to_ts):
        js = self.get_data_file_cached('delivery_report', 'delivery_report.txt')
        if not js: return
        
        lst = []
        for k,v in js['mons']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            if not v['work_secs']: continue
            lst.append( (k, round(v['lines'] * 100 / (float(v['work_secs']) / 3600), 2)) )
        
        return (('ProductivityRate',), lst)  
    
    def report_worker_productivity(self, frm_ts, to_ts):
        js = self.get_data_file_cached('delivery_report', 'delivery_report.txt')
        if not js: return
        
        dps = []
        for k,v in js['mons']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            if not v['work_secs']: continue
            dps.append( {'x': k * 1000, 'y': round(v['lines'] * 100 / (float(v['work_secs']) / 3600), 2), 'lines': len(v['lines'])} );
        
        chart_config = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "Worker Productivity"},
            'axisX': {'valueFormatString': "MMM-YYYY", 'labelAngle': -50},
            'data': [
                {'toolTipContent': '{x}: {y}, Lines: {lines}', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps}
            ]
        }
        return {'type':'chart', 'config': chart_config}
        
    def report_inventory_to_sales_ratio(self, frm_ts, to_ts):
        js = self.get_data_file_cached('receipt_report', 'receipt_report.txt')
        if not js: return
        
        dps = []
        for k,v in js['summary']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            if not v[3]: continue
            dps.append( {'x': k * 1000, 'y': round(v[1] * 100 / float(v[3][0]), 2)} );
        
        chart_config = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "Inventory To Sales Ratio"},
            'axisX': {'valueFormatString': "MMM-YYYY", 'labelAngle': -50},
            'data': [
                {'toolTipContent': '{x}: {y}', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps}
            ]
        }
        return {'type':'chart', 'config': chart_config}
        
    def export_report_inventory_to_sales_ratio(self, frm_ts, to_ts):
        js = self.get_data_file_cached('receipt_report', 'receipt_report.txt')
        if not js: return
        
        lst = []
        for k,v in js['summary']:
            if frm_ts and to_ts and (k < frm_ts or k > to_ts): continue
            if not v[3]: continue
            lst.append( (k, round(v[1] * 100 / float(v[3][0]), 2)) )
    
        return (('Inventory/Sales',), lst)
    
    def fn_export_reports(self):
        js = self.req.psv_js('js')
        
        frm_ts = to_ts = 0
        dt = js['frm_date']
        if dt: frm_ts = int(time.mktime(time.strptime(dt, "%Y-%m")))
        dt = js['to_date']
        if dt: to_ts = int(time.mktime(time.strptime(dt, "%Y-%m")))
        if not frm_ts or not to_ts: return
        
        frm_tp = time.localtime(frm_ts)
        to_tp = time.localtime(to_ts)
        min_d = frm_tp.tm_year * 12 + frm_tp.tm_mon
        max_d = to_tp.tm_year * 12 + to_tp.tm_mon
        len_d = max_d - min_d + 1
        
        hdr = ['', ]
        for i in range(min_d, max_d + 1):
            y,m = divmod(i, 12)
            hdr.append('%04d-%02d' % (y, m))
        
        rows = [hdr, ]
        for report in G_MAP_REPORTS:
            if not(self.user_lvl & report[1]): continue
            js = getattr(self, 'export_report_%s' % (report[2], ))(frm_ts, to_ts)
            if not js: continue
            
            i_rows = []
            hdr, lst = js
            for h in range( len(hdr) ):
                row = ['', ] * (len_d + 1)
                row[0] = hdr[h]
                i_rows.append(row)
            
            for l in lst:
                if l[0] == None: continue
                cur_tp = time.localtime(l[0])
                idx = cur_tp.tm_year * 12 + cur_tp.tm_mon - min_d
                
                for i in range(1, len(l)):
                    i_rows[i - 1][idx + 1] = (l[i] != None and str(l[i]) or '')
            
            i_rows.append( ['', ] * (len_d + 1) )
            rows.extend(i_rows)
        
        fp = cStringIO.StringIO()
        wt = csv.writer(fp)
        for r in rows: wt.writerow(r)
        
        self.req.out_headers['content-type'] = 'application/octet-stream'
        self.req.out_headers['content-disposition'] = 'attachment; filename="data.csv"'
        self.req.write( fp.getvalue() )
        
    
