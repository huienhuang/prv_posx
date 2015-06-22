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



CFG = {
    'id': 'SALESREPORT_C0000005',
    'name': 'Sales Report',
    'perm_list': [
    ('access', ''),
    ('admin', ''),
    ]
}

PERM_ADMIN = 1 << 1


BIT_PPL = (1 << config.BASE_ROLES_MAP['Sales']) | (1 << config.BASE_ROLES_MAP['Delivery'])
BIT_MGR = (1 << config.BASE_ROLES_MAP['SalesMgr']) | (1 << config.BASE_ROLES_MAP['DeliveryMgr'])


class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        perm = self.get_cur_rh_perm() & PERM_ADMIN

        r = {
            'tab_cur_idx' : 2,
            'title': 'Purchasing',
            'tabs': [ ('sale', 'Sale'), ('rect', 'Receipt'), ('customer', 'Customer')  ]
        }
        if perm: r['tabs'].append( ('cfg', 'Config') )

        self.req.writefile('tmpl_multitabs.html', r)

    
    def get_allowed_users(self):
        m = self.get_config_js('sales_report_allowed_users', {})
        if type(m) == list: m = {}

        return m

    def fn_cfg(self):
        aus = self.get_allowed_users()
        users = []
        for user in self.get_user_roles():
            if not user[2] & BIT_PPL: continue
            users.append( {'id': user[0], 'name': user[1], 'is_mgr': user[2] & BIT_MGR} )

        r = {
            'users': users,
            'aus': aus
        }
        self.req.writefile('sales_report__cfg.html', r)
        
    fn_cfg.PERM = PERM_ADMIN
    
    
    def fn_set_cfg(self):
        js = self.req.psv_js('js')
        
        d_users = dict([ (f_user[0], (f_user[1], f_user[2] & BIT_MGR)) for f_user in self.get_user_roles() if f_user[2] & BIT_PPL ])
        
        mgr_id = int(js['mgr_id'])
        if not d_users.get(mgr_id)[1]: return

        uids = dict([ (int(u), 1) for u in js['uids'] if int(u) in d_users ])

        aus = self.get_allowed_users()
        aus[mgr_id] = uids

        self.set_config_js('sales_report_allowed_users', aus)
        self.req.writejs({'err' : 0})
        
    fn_set_cfg.PERM = PERM_ADMIN
    
    def fn_export_csv(self):
        data = [ map(lambda f_x: f_x != None and unicode(f_x) or '', f_r) for f_r in self.req.psv_js('js') ]
        
        fp = cStringIO.StringIO()
        wt = csv.writer(fp)
        for r in data: wt.writerow(r)
        
        self.req.out_headers['content-type'] = 'application/octet-stream'
        self.req.out_headers['content-disposition'] = 'attachment; filename="data.csv"'
        self.req.write( fp.getvalue() )
        
    fn_export_csv.PERM = PERM_ADMIN
    
    def fn_sale(self):
        tp = time.localtime()
        if tp.tm_mon <= 2:
            dt = datetime.date(tp.tm_year - 1, 10 + tp.tm_mon, 1)
        else:
            dt = datetime.date(tp.tm_year, tp.tm_mon - 2, 1)

        to_dt = '%04d-%02d-%02d' % tp[:3]
        frm_dt = '%04d-%02d-01' % dt.timetuple()[:2]

        perm = self.get_cur_rh_perm() & PERM_ADMIN

        userlist = self.get_user_roles()
        if perm:
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & BIT_PPL ])
            sales_users.add('')
        else:
            aus = self.get_allowed_users().get(str(self.user_id), {str(self.user_id): 1})
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & BIT_PPL and aus.get(str(f_user[0])) ])
        
        self.req.writefile('sales_report__sale.html', {'const': const, 'sales_users': sorted(sales_users), 'frm_dt': frm_dt, 'to_dt': to_dt})
        
    
    def fn_get_sale_data(self):
        frm_tp = time.strptime(self.req.qsv_ustr('frm_dt'), '%Y-%m-%d')
        to_tp = time.strptime(self.req.qsv_ustr('to_dt'), '%Y-%m-%d')
        intval = self.req.qsv_int('intval')

        fi = frm_tp.tm_year * 10000 + frm_tp.tm_mon * 100 + frm_tp.tm_mday
        ti = to_tp.tm_year * 10000 + to_tp.tm_mon * 100 + to_tp.tm_mday

        js = self.get_data_file_cached('daily_sale', 'daily_sale.txt')['s'][intval]
        da = [ f_x[0] for f_x in js ]
        js = js[ bisect.bisect_left(da, fi): bisect.bisect_right(da, ti) ]

        perm = self.get_cur_rh_perm() & PERM_ADMIN

        userlist = self.get_user_roles()
        if perm:
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & BIT_PPL ])
            sales_users.add('')
        else:
            aus = self.get_allowed_users().get(str(self.user_id), {str(self.user_id): 1})
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & BIT_PPL and aus.get(str(f_user[0])) ])

        rjs = []
        for ds in js:
            m,d = divmod(ds[0], 100)
            y,m = divmod(m, 100)
            dd = {}
            rjs.append(['%04d-%02d-%02d' % (y, m, d), dd])

            for us in ds[1].items():
                unz = us[0]
                if unz not in sales_users: unz = ''
                if unz in sales_users:
                    dd[unz] = us[1]

        self.req.writejs(rjs)


    def fn_rect(self):
        tp = time.localtime()
        if tp.tm_mon <= 2:
            dt = datetime.date(tp.tm_year - 1, 10 + tp.tm_mon, 1)
        else:
            dt = datetime.date(tp.tm_year, tp.tm_mon - 2, 1)

        to_dt = '%04d-%02d-%02d' % tp[:3]
        frm_dt = '%04d-%02d-01' % dt.timetuple()[:2]

        perm = self.get_cur_rh_perm() & PERM_ADMIN

        userlist = self.get_user_roles()
        if perm:
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & BIT_PPL ])
            sales_users.add('')
        else:
            aus = self.get_allowed_users().get(str(self.user_id), {str(self.user_id): 1})
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & BIT_PPL and aus.get(str(f_user[0])) ])
        
        self.req.writefile('sales_report__rect.html', {'const': const, 'sales_users': sales_users, 'frm_dt': frm_dt, 'to_dt': to_dt})
        
    
    def fn_get_rect_data(self):
        frm_tp = time.strptime(self.req.qsv_ustr('frm_dt'), '%Y-%m-%d')
        to_tp = time.strptime(self.req.qsv_ustr('to_dt'), '%Y-%m-%d')
        intval = self.req.qsv_int('intval')

        fi = frm_tp.tm_year * 10000 + frm_tp.tm_mon * 100 + frm_tp.tm_mday
        ti = to_tp.tm_year * 10000 + to_tp.tm_mon * 100 + to_tp.tm_mday

        js = self.get_data_file_cached('daily_sale', 'daily_sale.txt')['n'][intval]
        da = [ f_x[0] for f_x in js ]
        js = js[ bisect.bisect_left(da, fi): bisect.bisect_right(da, ti) ]

        perm = self.get_cur_rh_perm() & PERM_ADMIN
        
        userlist = self.get_user_roles()
        if perm:
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & BIT_PPL ])
            sales_users.add('')
        else:
            aus = self.get_allowed_users().get(str(self.user_id), {str(self.user_id): 1})
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & BIT_PPL and aus.get(str(f_user[0])) ])

        rjs = []
        for ds in js:
            m,d = divmod(ds[0], 100)
            y,m = divmod(m, 100)
            dd = {}
            rjs.append(['%04d-%02d-%02d' % (y, m, d), dd])

            for us in ds[1].items():
                unz = us[0]
                if unz not in sales_users: unz = ''
                if unz in sales_users:
                    dd[unz] = us[1]

        self.req.writejs(rjs)


    def fn_customer(self):
        perm = self.get_cur_rh_perm() & PERM_ADMIN

        userlist = self.get_user_roles()
        if perm:
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & BIT_PPL ])
            sales_users.add('')
        else:
            aus = self.get_allowed_users().get(str(self.user_id), {str(self.user_id): 1})
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & BIT_PPL and aus.get(str(f_user[0])) ])
        
        self.req.writefile('sales_report__customer.html', {'const': const, 'sales_users': sales_users})


    def fn_get_customer_data(self):
        js = self.req.psv_js('js')

        frm_tp = time.strptime(js['frm_dt'], '%m/%d/%Y')
        to_tp = time.strptime(js['to_dt'], '%m/%d/%Y')
        intval = int(js['intval'])
        cates = js.get('cates') or []
        users = js.get('users') or []

        fi = frm_tp.tm_year * 10000 + frm_tp.tm_mon * 100 + frm_tp.tm_mday
        ti = to_tp.tm_year * 10000 + to_tp.tm_mon * 100 + to_tp.tm_mday


        ts = time.time()
        fz = self.get_data_file_cached('daily_sale', 'daily_sale_2.txt')
        ts = ts - time.time()

        cz = fz['z']

        js = fz['c'][intval]
        da = [ f_x[0] for f_x in js ]
        js = js[ bisect.bisect_left(da, fi): bisect.bisect_right(da, ti) ]

        perm = self.get_cur_rh_perm() & PERM_ADMIN
        userlist = self.get_user_roles()
        if perm:
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & BIT_PPL ])
            sales_users.add('')
        else:
            aus = self.get_allowed_users().get(str(self.user_id), {str(self.user_id): 1})
            sales_users = set([ f_user[1].lower() for f_user in userlist if f_user[2] & BIT_PPL and aus.get(str(f_user[0])) ])

        users = set(users) & sales_users
        cates = set(cates)

        hdr = set()
        cust = {}

        for di,d_users in js:
            for clerk,d_custs in d_users.items():
                if clerk not in sales_users: clerk = ''
                if clerk not in users: continue

                for cid,d_cates in d_custs.items():
                    if cid == None: continue

                    for cate,dd in d_cates.items():
                        if not const.ITEM_D_CATE2.has_key(cate): cate = ''
                        if cate not in cates: continue

                        v = round(dd[0], 5)

                        hdr.add(di)
                        ds = cust.setdefault(cid, {}).setdefault(di, {})
                        ds.setdefault('$', [0])[0] += v
                        ds.setdefault(cate, {}).setdefault(clerk, [0])[0] += v

        n_cz = []
        for cid,v in cust.items(): n_cz.append( (str(cid), v, cz.get(cid, '')) )
        n_cz.sort(key=lambda f_x:f_x[2].lower())

        self.req.writejs({'hdr': sorted(hdr), 'cust': n_cz, 'ts': ts})



