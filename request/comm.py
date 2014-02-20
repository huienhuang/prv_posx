import sys
import os
import glob
import json
import config
import cPickle
import const

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
        reports = map(lambda n: os.path.basename(n)[:-7], glob.glob(self.req.app.app_dir + '/data/*_df.txt'))
        users = self.getuserlist()
        perm_sales = 1 << config.USER_PERM_BIT['sales']
        sales = [ x for x in users if x[2] & perm_sales and x[0] != 1 ]
        
        self.req.writefile('comm_by_dept.html', {'reports': reports, 'sales': sales, 'const': const})
    
    USER_MAP = {
        'sales1': 'ray',
        'sales2': 'anthony',
        'sales3': 'joe',
        'sales8': 'nicole',
        'sales5': 'jimmy',
        'sales6': 'sally',
    }
    def fn_get_comm(self):
        report_date = self.qsv_str('date').replace('-', '')
        if not report_date.isdigit(): return
        
        datafile = '%s/data/%s-%s-%s_df.txt' % (self.req.app.app_dir, report_date[:4], report_date[4:6], report_date[6:8])
        if not os.path.exists(datafile): return
        receipts, depts, cates, errs = cPickle.load( open(datafile, 'rb') )
        
        clerks = {}
        for num,r in receipts.items():
            is_invoice = r['is_invoice']
            included = r['included']
            qb = r.get('qb')
            for itemsid, clerk, price, qty, deptsid in r['items']:
                clerk = self.USER_MAP.get(clerk, clerk)
                p = clerks.setdefault(clerk, {}).setdefault(deptsid, [0, 0, 0])
                
                if included:
                    if not is_invoice or qb:
                        p[1] += price
                    else:
                        p[0] += price
                else:
                    p[2] += price
        
        a_clerks = []
        for f_clerk,f_depts in sorted(clerks.items(), key=lambda f_x: f_x[0]):
            f_depts = [ (str(f_x[0]), f_x[1], depts.get(f_x[0]) or ['', 0]) for f_x in f_depts.items() ]
            f_depts.sort(key=lambda f_x: f_x[2][0].lower())
            a_clerks.append( (f_clerk, f_depts) )
        
        r = {
            'cates': sorted(cates.items(), key=lambda f_x: f_x[0]),
            'clerks': a_clerks,
            'depts': depts,
            'err': '\n'.join(errs),
        }
        self.req.writejs(r)
        
