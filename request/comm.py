import sys
import os
import glob
import json
import config
import cPickle
import const
import time

DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/basehandler').RequestHandler):

    def fn_default(self):
        crs = map(lambda n: os.path.basename(n)[:-7],  glob.glob(self.req.app.app_dir + '/data/*_cr.txt'))
        
        data = {'crs': crs}
        self.req.writefile('comm.html', data)

    def fn_cr(self):
        ul = []
        t = self.qsv_str('date')
        err = None
        if t and t.isdigit():
            p = '%s/data/%s-%s-%s' % (self.req.app.app_dir, t[:4], t[4:6], t[6:8])
            f = p + '_cr.txt'
            if os.path.exists(f):
                c,r = json.load(open(f, 'rb'))
                for k, v in sorted(c.items(), key=lambda x:x[0].lower()):
                    #r0 = [ [kk] + vv + r[kk] for kk,vv in sorted(v[-2].items(), key=lambda x:(r[x[0]][1],x[1][1] > 0,int(x[0]))) ]
                    #r1 = [ [kk] + vv + r[kk] for kk,vv in sorted(v[-1].items(), key=lambda x:(r[x[0]][1],x[1][1] > 0,int(x[0]))) ]
                    r0 = [ [kk] + vv + r[kk] for kk,vv in sorted(v[-2].items(), key=lambda x:(int(x[0]))) ]
                    r1 = [ [kk] + vv + r[kk] for kk,vv in sorted(v[-1].items(), key=lambda x:(int(x[0]))) ]
                    
                    ul.append( [k] + v[:-2] + [r0, r1] )
            
            e = p + '_er.txt'
            if os.path.exists(e): err = open(e, 'rb').read()
            
        o = {'date': t, 'userlist': ul, 'err':err}
        self.req.writejs(o)


    def fn_comm_by_dept(self):
        reports_0 = map(lambda n: os.path.basename(n)[:-16], glob.glob(self.req.app.app_dir + '/data/*_comm_clerks.txt'))
        reports_1 = map(lambda n: os.path.basename(n)[:-9], glob.glob(self.req.app.app_dir + '/data/*_comm.txt'))
        
        s = set(reports_0)
        reports = list(s.union(reports_1))
        reports.sort()
        
        self.req.writefile('comm_by_dept.html', {'reports': reports, 'const': const})
    
    USER_MAP = {
        'sales1': 'ray',
        'sales2': 'anthony',
        'sales3': 'joe',
        'sales8': 'nicole',
        'sales5': 'jimmy',
        'sales6': 'sally',
    }
    def fn_get_comm(self):
        months = self.qsv_str('months').split('|')
        
        js = {}
        for m in months:
            if not m.replace('-', '').isdigit(): continue
            datafile = '%s/data/%s_comm_clerks.txt' % (self.req.app.app_dir, m)
            if not os.path.exists(datafile):
                datafile = '%s/data/%s_comm.txt' % (self.req.app.app_dir, m)
                if not os.path.exists(datafile): return
                
            js[ m ] = cPickle.load( open(datafile, 'rb') )
            
        self.req.writejs(js)

    def fn_get_comm_rate(self):
        rates = self.get_config_js('comm_rates', {})
        self.req.writejs({'rates': rates})


    def fn_set_comm_rate(self):
        js = self.req.psv_js('js')
        js = dict([ ( unicode(f_x[0]).lower(), (round(float(f_x[1]), 1), round(float(f_x[2]), 1)) ) for f_x in js ])

        self.set_config_js('comm_rates', js)
        self.req.writejs({'ret': 1})

    def fn_get_comm_rate_v2(self):
        rates = self.get_config_js('comm_rates', {})

        cate_rates = []
        for f_cate,f_type in const.ITEM_L_CATE2:
            r = rates.get(f_type.lower())
            if r:
                rate = ( round(r[0] / 100.0, 5), round(r[1] / 100.0, 5) )
            else:
                rate = (0, 0)
            cate_rates.append( (f_cate, rate) )
            
        cate_rates = dict(cate_rates)
        self.req.writejs({'cate_rates': cate_rates})