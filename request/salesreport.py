import json
import time
import config
import datetime
import glob
import os
import const


DEFAULT_PERM = 1 << config.USER_PERM_BIT['sales_mgr']
class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('sales_report_frame.html')
    
    def fn_sale(self):
        reports = map(lambda n: os.path.basename(n)[:-16], glob.glob(self.req.app.app_dir + '/data/*_comm_clerks.txt'))
        reports.sort()
        
        tp = time.localtime()
        dt = "%04d-%02d-%02d" % (tp.tm_year, tp.tm_mon, 1)
        if not reports or reports[-1] != dt: reports.append(dt)
        
        self.req.writefile('sales_report__sale.html', {'reports': reports, 'const': const})
        
    
    sales_users = set(['ray', 'anthony', 'hilda'])
    def fn_get_sale_data(self):
        months = self.qsv_str('months').split('|')
        
        jss = {}
        for i in range(len(months)):
            m = months[i]
            if not m.replace('-', '').isdigit(): return
            datafile = '%s/data/%s_comm_clerks.txt' % (self.req.app.app_dir, m)
            if not os.path.exists(datafile):
                datafile = '%s/data/%s_comm.txt' % (self.req.app.app_dir, m)
                if not os.path.exists(datafile): return
                js = self.get_comm_js(m)
            else:
                js = self.get_comm_clerks_js(m)
            
            jss[m] = dict([ f_v for f_v in js[0].items() if f_v[0] in self.sales_users ]) 
        
        self.req.writejs(jss)
        
    
    def fn_rect(self):
        reports = map(lambda n: os.path.basename(n)[:-16], glob.glob(self.req.app.app_dir + '/data/*_comm_clerks.txt'))
        reports.sort()
        
        tp = time.localtime()
        dt = "%04d-%02d-%02d" % (tp.tm_year, tp.tm_mon, 1)
        if not reports or reports[-1] != dt: reports.append(dt)
        
        self.req.writefile('sales_report__rect.html', {'reports': reports, 'const': const})
        
    
    def fn_get_rect_data(self):
        months = self.qsv_str('months').split('|')
        
        jss = {}
        for i in range(len(months)):
            m = months[i]
            if not m.replace('-', '').isdigit(): return
            datafile = '%s/data/%s_comm_clerks.txt' % (self.req.app.app_dir, m)
            if not os.path.exists(datafile):
                datafile = '%s/data/%s_comm.txt' % (self.req.app.app_dir, m)
                if not os.path.exists(datafile): return
                js = self.get_comm_js(m)
            else:
                js = self.get_comm_clerks_js(m)
            
            if len(js) <= 2:
                jss[m] = {}
            else:
                jss[m] = dict([ f_v for f_v in js[2].items() if f_v[0] in self.sales_users ]) 
        
        self.req.writejs(jss)
        
        