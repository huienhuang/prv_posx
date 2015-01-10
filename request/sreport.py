import sys
import os
import glob
import json
import config
import cPickle
import const
import time
import datetime
import bisect
import cStringIO
import csv

DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        r = {
            'tab_cur_idx' : 3,
            'title': 'Sales Report',
            'tabs': [
                ('year_to_year', 'YearToYear'),
                ('sale_by_month', 'SaleByMonth'),
                ('$reportgeneral', 'General'),
                ('$reportdaily', 'Daily'),
            ]
        }
        self.req.writefile('tmpl_multitabs.html', r)

    def fn_get_customer_sale(self):
        cid = self.req.qsv_int('cid')
        rjs = (self.get_data_file_cached('receipt_report', 'receipt_report.txt') or {}).get('customer', {})
        ms = rjs.get(cid) or []
        
        ym = []
        for mts,msa in ms:
            tp = time.localtime(mts)
            if not ym or ym[-1][0] != tp.tm_year: ym.append( (tp.tm_year, [0,] * 12) )
            m = ym[-1][1]
            m[tp.tm_mon - 1] += msa[0]
        
        self.req.writejs(ym)

    def fn_get_sale(self):
        rjs = (self.get_data_file_cached('receipt_report', 'receipt_report.txt') or {}).get('summary', [])
        ms = rjs
        
        ym = []
        for mts,msa in ms:
            tp = time.localtime(mts)
            if not ym or ym[-1][0] != tp.tm_year: ym.append( (tp.tm_year, [0,] * 12) )
            m = ym[-1][1]
            m[tp.tm_mon - 1] += msa[1]
        
        self.req.writejs(ym)

    def fn_sale_by_month(self):
        self.req.writefile('report/sale_by_month.html')

    def fn_year_to_year(self):
        yrs = {}
        rjs = (self.get_data_file_cached('receipt_report', 'receipt_report.txt') or {}).get('summary', [])
        for r in rjs:
            yrs.setdefault(time.localtime(r[0]).tm_year, [0])[0] += r[1][1]
        yrs = yrs.items()
        yrs.sort(key=lambda f_x: f_x[0])
        dps = []
        for yr,amt in yrs:
            dps.append({'label': yr, 'y': round(amt[0], 2)})
        
        cfg = {
            'zoomEnabled': True,
            'theme': "theme2",
            'title': {'text': "Year To Year"},
            'axisY': {'title':"Total Sale $"},
            'data': [
                {'type': "column", 'dataPoints': dps},
            ]
        }
        
        self.req.writefile('report/year_to_year.html', {'chart_cfg': json.dumps(cfg, separators=(',',':'))})

    def fn_transaction(self):
        
        self.req.writefile('report/transaction.html')
        
    def fn_cust_by_dept(self):
        r = {
            'const': const
        }
        self.req.writefile('cust_by_dept.html', r)
    


    def get_cust_sales(self, frm, to):
        frm_ts = to_ts = 0
        if frm: frm_ts = int(time.mktime(time.strptime(frm, "%Y-%m")))
        if to: to_ts = int(time.mktime(time.strptime(to, "%Y-%m")))
        if frm_ts > to_ts: return []

        cust_l = (self.get_data_file_cached('receipt_report', 'receipt_report.txt') or {}).get('customer', {}).items()
        cust_l.sort(key=lambda f_x:f_x[0])

        n_cust_l = []
        for f_cid,f_dt_l in cust_l:
            ldt_k = [ f_x[0] for f_x in f_dt_l ]
            ttl_sales = 0
            for dt in f_dt_l[bisect.bisect_left(ldt_k, frm_ts):bisect.bisect_right(ldt_k, to_ts)]:
                ttl_sales += dt[1][0]
            if ttl_sales: n_cust_l.append( (f_cid, ttl_sales) )

        return n_cust_l

    def fn_export_cust_sales(self):
        js = self.req.psv_js('js')
        n_cust_l = self.get_cust_sales(js.get('frm'), js.get('to'))
        if not n_cust_l: return

        cust_d = {}
        cur = self.cur()
        cur.execute('select sid,name,detail from sync_receipts_customers where sid in (%s)' % ( ','.join([str(f_x[0]) for f_x in n_cust_l]) ))
        for r in cur.fetchall(): cust_d[ r[0] ] = r

        data = [ ('Name', 'Address', 'Phone', 'Sales') ]
        for cid,sales in n_cust_l:
            sid,name,detail = cust_d.get(cid)
            gjs = json.loads(detail)
            addr = []

            addr1 = gjs.get('addr1') or gjs.get('address1') or ''
            addr2 = gjs.get('addr2') or gjs.get('address2') or ''
            addr.append(addr1 + (addr2 and ' ' + addr2 or ''))

            addr.append(gjs['city'])
            addr.append(gjs['state'] + (gjs['zip'] and ' ' + gjs['zip'] or ''))
            phone = gjs.get('phone') or gjs.get('phone1') or ''

            r = (
                name,
                ','.join([f_a for f_a in addr if f_a]),
                phone,
                sales and '%0.2f' % (sales, ) or '',
            )
            data.append(r)

        fp = cStringIO.StringIO()
        wt = csv.writer(fp)
        for r in data: wt.writerow(r)
        
        self.req.out_headers['content-type'] = 'application/octet-stream'
        self.req.out_headers['content-disposition'] = 'attachment; filename="data.csv"'
        self.req.write( fp.getvalue() )

    def fn_get(self):
        ret = {'res':{'len':0, 'apg':[]}}

        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        n_cust_l = self.get_cust_sales(self.qsv_str('frm'), self.qsv_str('to'))
        rlen = len(n_cust_l)

        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            n_cust_l = n_cust_l[sidx * pgsz : sidx * pgsz + (eidx - sidx) * pgsz]
            if n_cust_l:
                cust_d = {}
                cur.execute('select sid,name,detail from sync_receipts_customers where sid in (%s)' % ( ','.join([str(f_x[0]) for f_x in n_cust_l]) ))
                for r in cur.fetchall(): cust_d[ r[0] ] = r

            for cid,sales in n_cust_l:
                sid,name,detail = cust_d.get(cid)
                gjs = json.loads(detail)
                addr = []

                addr1 = gjs.get('addr1') or gjs.get('address1') or ''
                addr2 = gjs.get('addr2') or gjs.get('address2') or ''
                addr.append(addr1 + (addr2 and ' ' + addr2 or ''))

                addr.append(gjs['city'])
                addr.append(gjs['state'] + (gjs['zip'] and ' ' + gjs['zip'] or ''))
                phone = gjs.get('phone') or gjs.get('phone1') or ''

                r = (
                    name,
                    ','.join([f_a for f_a in addr if f_a]),
                    phone,
                    sales and '%0.2f' % (sales, ) or '',
                    str(sid)
                )
                apg.append(r)

        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
