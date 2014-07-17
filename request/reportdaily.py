import json
import os
import time
import config
import re
import datetime
import cStringIO
import csv
import cPickle


PERM_ADMIN = 1 << config.USER_PERM_BIT['admin']

G_MAP_REPORTS = [
    ('po', PERM_ADMIN, 'po'),
    ('delivery', PERM_ADMIN, 'delivery'),
    ('sales', PERM_ADMIN, 'sales'),
]

DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        reports = []
        for i in range(len(G_MAP_REPORTS)):
            report = G_MAP_REPORTS[i]
            if not(self.user_lvl & report[1]): continue
            reports.append( (i, report[0]) )
        
        self.req.writefile('report_daily.html', {'reports': reports})
        
        
    def fn_get_report(self):
        frm_ts = 0
        dt = self.qsv_str('frm')
        if dt: frm_ts = int(time.mktime(time.strptime(dt, "%Y-%m")))
        if not frm_ts:
            dt = datetime.date.today()
            frm_ts = int(time.mktime(datetime.date(dt.year, dt.month, 1).timetuple()))
        dt = datetime.date.fromtimestamp(frm_ts)
        yr = dt.year
        mn = dt.month + 1
        if mn > 12:
            yr += 1
            mn = 1
        to_ts = int(time.mktime(datetime.date(yr, mn, 1).timetuple()))
        
        report_idx = self.qsv_int('idx')
        if report_idx < 0 or report_idx >= len(G_MAP_REPORTS): return
        
        report = G_MAP_REPORTS[report_idx]
        if not(self.user_lvl & report[1]): return
        
        js = getattr(self, 'report_%s' % (report[2], ))(frm_ts, to_ts)
        self.req.writejs(js)
    
    def fn_get_reports(self):
        frm_ts = 0
        dt = self.qsv_str('frm')
        if dt: frm_ts = int(time.mktime(time.strptime(dt, "%Y-%m")))
        if not frm_ts:
            dt = datetime.date.today()
            frm_ts = int(time.mktime(datetime.date(dt.year, dt.month, 1).timetuple()))
        dt = datetime.date.fromtimestamp(frm_ts)
        yr = dt.year
        mn = dt.month + 1
        if mn > 12:
            yr += 1
            mn = 1
        to_ts = int(time.mktime(datetime.date(yr, mn, 1).timetuple()))
        
        lst = []
        for report in G_MAP_REPORTS:
            if not(self.user_lvl & report[1]): continue
            js = getattr(self, 'report_%s' % (report[2], ))(frm_ts, to_ts)
            lst.append(js)
        self.req.writejs(lst)
    
    def report_po(self, frm_ts, to_ts):
        cur = self.cur()
        cur.execute('select * from sync_purchaseorders where status<=1 and podate>=%s and podate<%s', (
            frm_ts, to_ts
            )
        )
        cnz = cur.column_names
        amts = {}
        for r in cur.fetchall():
            r = dict(zip(cnz, r))
            gjs = json.loads(r['global_js'])
            
            dt = datetime.date.fromtimestamp(r['podate'])
            ts = int(time.mktime(datetime.date(dt.year, dt.month, dt.day).timetuple()))
            amt = amts.setdefault(ts, [0, 0.0])
            amt[0] += 1
            amt[1] += gjs['total']
        
        dps_0 = []
        dps_1 = []
        for ts, amt in sorted(amts.items(), key=lambda f_x: f_x[0]):
            dps_0.append( {'x': ts * 1000, 'y': round(amt[1] / amt[0], 2)} );
            dps_1.append( {'x': ts * 1000, 'y': amt[0]} );
        
        chart_config = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "PO"},
            'axisY': {'title':"AVG"},
            'axisY2': {'title':"COUNT"},
            'axisX': {'valueFormatString': "MMM-DD", 'labelAngle': -50},
            'data': [
                {'showInLegend': True, 'name': 'AVG', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps_0},
                {'showInLegend': True, 'name': 'COUNT', 'axisYType': 'secondary', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps_1}
            ]
        }
        return {'type':'chart', 'config': chart_config}
    
    def report_delivery(self, frm_ts, to_ts):
        cur = self.cur()
        
        records = {}
        cur.execute("select d_id,ts from deliveryv2 where ts>=%s and ts<%s", (frm_ts, to_ts))
        for r in cur.fetchall():
            dt = time.localtime(r[1])
            records[ r[0] ] = ( int(time.mktime(datetime.date(dt.tm_year, dt.tm_mon, dt.tm_mday).timetuple())), r[1] )
        if not records: return
        
        cur.execute('select dr.d_id,sr.* from deliveryv2_receipt dr left join sync_receipts sr on (dr.num=sr.num) where dr.d_id in ('+','.join(map(str, records.keys()))+')')
        cnz = cur.column_names
        amts = {}
        for r in cur.fetchall():
            r = dict(zip(cnz, r))
            
            record = records.get(r['d_id'])
            if not record: continue
            
            items = json.loads(r['items_js'])
            glbs = json.loads(r['global_js'])
            
            rtype = (r['type'] >> 8) & 0xFF
            disc = (100 - glbs['discprc']) / 100
            
            total_price = 0
            for t in items:
                if t['itemsid'] == 1000000005: continue
                total_price += t['price'] * t['qty']
            total_price *= disc
            
            s = amts.setdefault(record[0], [0, 0.0])
            if rtype > 0:
                s[0] -= 1
                s[1] -= total_price
            else:
                s[0] += 1
                s[1] += total_price
        
        dps_0 = []
        dps_1 = []
        for ts, amt in sorted(amts.items(), key=lambda f_x: f_x[0]):
            if not amt[0]: continue
            dps_0.append( {'x': ts * 1000, 'y': round(amt[1] / amt[0], 2)} );
            dps_1.append( {'x': ts * 1000, 'y': amt[0]} );
        
        chart_config = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "Delivery"},
            'axisY': {'title':"AVG"},
            'axisY2': {'title':"COUNT"},
            'axisX': {'valueFormatString': "MMM-DD", 'labelAngle': -50},
            'data': [
                {'showInLegend': True, 'name': 'AVG', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps_0},
                {'showInLegend': True, 'name': 'COUNT', 'axisYType': 'secondary', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps_1}
            ]
        }
        return {'type':'chart', 'config': chart_config} 
    
    def report_sales(self, frm_ts, to_ts):
        cur = self.cur()
        
        cur.execute('select * from sync_receipts where sid_type=0 and (type&0xFF00)<0x0200 and order_date>=%s and order_date<%s', (frm_ts, to_ts))
        cnz = cur.column_names
        amts = {}
        for r in cur.fetchall():
            r = dict(zip(cnz, r))
            
            items = json.loads(r['items_js'])
            glbs = json.loads(r['global_js'])
            
            rtype = (r['type'] >> 8) & 0xFF
            disc = (100 - glbs['discprc']) / 100
            
            total_price = 0
            for t in items:
                if t['itemsid'] == 1000000005: continue
                total_price += t['price'] * t['qty']
            total_price *= disc
            
            dt = datetime.date.fromtimestamp(r['order_date'])
            ts = int(time.mktime(datetime.date(dt.year, dt.month, dt.day).timetuple()))
            s = amts.setdefault(ts, [0, 0.0])
            if rtype > 0:
                s[0] -= 1
                s[1] -= total_price
            else:
                s[0] += 1
                s[1] += total_price
                
        
        cur.execute('select * from sorder where (ord_flag&8)!=0 and ord_order_date>=%s and ord_order_date<%s', (frm_ts, to_ts))
        nzs = cur.column_names
        for r in cur:
            r = dict(zip(nzs, r))
            
            items = json.loads(r['ord_items_js'])
            glbs = json.loads(r['ord_global_js'])
            
            rtype = r['ord_flag'] & (1 << 1)
            disc = (100 - glbs['disc']) / 100
            
            total_price = 0
            for t in items:
                total_price +=  t['in_price'] * t['in_qty']
            total_price *= disc
            
            dt = datetime.date.fromtimestamp(r['ord_order_date'])
            ts = int(time.mktime(datetime.date(dt.year, dt.month, dt.day).timetuple()))
            s = amts.setdefault(ts, [0, 0.0])
            if rtype > 0:
                s[0] -= 1
                s[1] -= total_price
            else:
                s[0] += 1
                s[1] += total_price
        
        dps_0 = []
        dps_1 = []
        for ts, amt in sorted(amts.items(), key=lambda f_x: f_x[0]):
            if not amt[0]: continue
            dps_0.append( {'x': ts * 1000, 'y': round(amt[1] / amt[0], 2)} );
            dps_1.append( {'x': ts * 1000, 'y': amt[0]} );
        
        chart_config = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "Sales"},
            'axisY': {'title':"AVG"},
            'axisY2': {'title':"COUNT"},
            'axisX': {'valueFormatString': "MMM-DD", 'labelAngle': -50},
            'data': [
                {'showInLegend': True, 'name': 'AVG', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps_0},
                {'showInLegend': True, 'name': 'COUNT', 'axisYType': 'secondary', 'type': "line", 'xValueType': "dateTime", 'dataPoints': dps_1}
            ]
        }
        return {'type':'chart', 'config': chart_config}
    
    
    def fn_get_inv(self):
        tp = map(int, self.req.qsv_str('frm_date').split('-'))
        frm_ts = int(time.mktime(datetime.date(tp[0], tp[1], tp[2]).timetuple()))
        
        cur = self.cur()
        cur.execute('select di_js from daily_inventory where di_ts=%s', (frm_ts,))
        rows = cur.fetchall()
        if not rows: return
        
        depts = sorted(cPickle.loads(rows[0][0])[1].items(), key=lambda f_x: f_x[0])
    
        self.req.writejs(depts)
    
    fn_get_inv.PERM = 1 << config.USER_PERM_BIT['accountingv2']
    
    def fn_view_inv(self):
        self.req.writefile('accounting_inv.html')
    
    fn_view_inv.PERM = 1 << config.USER_PERM_BIT['accountingv2']

