import json
import time
import config
import datetime
import glob
import os
import const
import json
import cStringIO
import csv
import bisect

SALES_PERM = 1 << config.USER_PERM_BIT['sales']
ADMIN_PERM = 1 << config.USER_PERM_BIT['admin']
SMGRS_PERM = 1 << config.USER_PERM_BIT['sales_mgr']
DMGRS_PERM = 1 << config.USER_PERM_BIT['delivery_mgr_adv']


DEFAULT_PERM = SMGRS_PERM | DMGRS_PERM
class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('sales_report_frame.html')
    
    
    def get_allowed_users(self):
        m = self.get_config_js('sales_report_allowed_users', {})
        if type(m) == list: m = {}

        return m

    def fn_cfg(self):
        aus = self.get_allowed_users()
        users = []
        for user in self.getuserlist():
            if not user[2] & SALES_PERM: continue
            users.append( {'id': user[0], 'name': user[1], 'is_mgr': user[2] & DEFAULT_PERM} )

        r = {
            'users': users,
            'aus': aus
        }
        self.req.writefile('sales_report__cfg.html', r)
        
    fn_cfg.PERM = ADMIN_PERM
    
    
    def fn_set_cfg(self):
        js = self.req.psv_js('js')
        
        d_users = dict([ (f_user[0], (f_user[1], f_user[2] & DEFAULT_PERM)) for f_user in self.getuserlist() if f_user[2] & SALES_PERM ])
        
        mgr_id = int(js['mgr_id'])
        if not d_users.get(mgr_id)[1]: return

        uids = dict([ (u, 1) for u in js['uids'] if int(u) in d_users ])

        aus = self.get_allowed_users()
        aus[mgr_id] = uids

        self.set_config_js('sales_report_allowed_users', aus)
        self.req.writejs({'err' : 0})
        
    fn_set_cfg.PERM = ADMIN_PERM
    
    def fn_export_csv(self):
        data = [ map(lambda f_x: f_x != None and unicode(f_x) or '', f_r) for f_r in self.req.psv_js('js') ]
        
        fp = cStringIO.StringIO()
        wt = csv.writer(fp)
        for r in data: wt.writerow(r)
        
        self.req.out_headers['content-type'] = 'application/octet-stream'
        self.req.out_headers['content-disposition'] = 'attachment; filename="data.csv"'
        self.req.write( fp.getvalue() )
        
    fn_export_csv.PERM = ADMIN_PERM
    
    def fn_sale(self):
        tp = time.localtime()
        if tp.tm_mon <= 2:
            dt = datetime.date(tp.tm_year - 1, 10 + tp.tm_mon, 1)
        else:
            dt = datetime.date(tp.tm_year, tp.tm_mon - 2, 1)

        to_dt = '%04d-%02d-%02d' % tp[:3]
        frm_dt = '%04d-%02d-01' % dt.timetuple()[:2]

        userlist = self.getuserlist()
        if self.user_lvl & ADMIN_PERM:
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & SALES_PERM ])
        else:
            aus = self.get_allowed_users().get(str(self.user_id), {})
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & SALES_PERM and aus.get(str(f_user[0])) ])
        
        self.req.writefile('sales_report__sale.html', {'const': const, 'sales_users': sales_users, 'frm_dt': frm_dt, 'to_dt': to_dt})
        
    
    def fn_get_sale_data(self):
        frm_tp = time.strptime(self.req.qsv_ustr('frm_dt'), '%Y-%m-%d')
        to_tp = time.strptime(self.req.qsv_ustr('to_dt'), '%Y-%m-%d')
        intval = self.req.qsv_int('intval')

        fi = frm_tp.tm_year * 10000 + frm_tp.tm_mon * 100 + frm_tp.tm_mday
        ti = to_tp.tm_year * 10000 + to_tp.tm_mon * 100 + to_tp.tm_mday

        js = self.get_data_file_cached('daily_sale', 'daily_sale.txt')[intval]
        da = [ f_x[0] for f_x in js ]
        js = js[ bisect.bisect_left(da, fi): bisect.bisect_right(da, ti) ]

        userlist = self.getuserlist()
        if self.user_lvl & ADMIN_PERM:
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & SALES_PERM ])
        else:
            aus = self.get_allowed_users().get(str(self.user_id), {})
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & SALES_PERM and aus.get(str(f_user[0])) ])

        rjs = []
        for ds in js:
                m,d = divmod(ds[0], 100)
                y,m = divmod(m, 100)
                dd = {}
                rjs.append(['%04d-%02d-%02d' % (y, m, d), dd])

                for us in ds[1].items():
                    if us[0] in sales_users:
                        dd[us[0]] = us[1]

        self.req.writejs(rjs)


    def fn_rect(self):
        reports = map(lambda n: os.path.basename(n)[:-16], glob.glob(self.req.app.app_dir + '/data/*_comm_clerks.txt'))
        reports.sort()
        
        tp = time.localtime()
        dt = "%04d-%02d-%02d" % (tp.tm_year, tp.tm_mon, 1)
        if not reports or reports[-1] != dt: reports.append(dt)
        
        userlist = self.getuserlist()
        if self.user_lvl & ADMIN_PERM:
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & SALES_PERM ])
        else:
            aus = self.get_allowed_users().get(str(self.user_id), {})
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & SALES_PERM and aus.get(str(f_user[0])) ])
            
        self.req.writefile('sales_report__rect.html', {'reports': reports, 'const': const, 'sales_users': sales_users})
        
    
    def fn_get_rect_data(self):
        months = self.qsv_str('months').split('|')
        
        userlist = self.getuserlist()
        if self.user_lvl & ADMIN_PERM:
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & SALES_PERM ])
        else:
            aus = self.get_allowed_users().get(str(self.user_id), {})
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & SALES_PERM and aus.get(str(f_user[0])) ])
            
        jss = {}
        _jss = self.get_data_files(months)
        for m,js in _jss.items():
            if len(js) <= 2:
                jss[m] = {}
            else:
                jss[m] = dict([ f_v for f_v in js[2].items() if f_v[0] in sales_users ])
        
        self.req.writejs(jss)


