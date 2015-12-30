import time
import config

CFG = {
    'id': 'HOME_BBBBBBBB',
    'name': 'Home',
    'perm_list': [
    ('access', ''),
    ]
}

class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        user_agent = self.environ.get('HTTP_USER_AGENT') or ''
        if user_agent and user_agent.lower().find('android') >= 0:
            self.req.redirect('mobile')
        else:
            self.go_default()
        
    def go_default(self):
        app_lku = dict([(f_x[2], f_x) for f_x in self.get_app_lst()])
        user_perms = self.get_user_perms()

        depts = self.get_config_js('APPS_BY_DEPTS', [])
        if self.user_id != 1:
            n_depts = []
            for v in depts:
                apps = []
                for app in v['apps']:
                    cfg,md,nz = app_lku.get(app['md'])
                    if not md: continue
                    if not self.has_perm(app['fn'], md.RequestHandler): continue
                    apps.append(app)
                
                if apps: n_depts.append({'name': v['name'], 'apps': apps})

            depts = n_depts

        self.req.writefile('home.html', {'depts': depts, 'user_id': self.user_id, 'user_name': '%s (%s)' % (self.user_name, getattr(config, 'store_name', None))})
        
    def fn_password(self):
        old_passwd = self.req.psv_ustr('old_passwd', '')
        new_passwd = self.req.psv_ustr('new_passwd', '')
        self.req.writejs( {'res': int(self.updpasswd(old_passwd, new_passwd))} )
        
    
    def fn_env(self):
        self.req.writefile('env.html', {'env':self.environ})
    
    
    def fn_set_password(self):
        self.req.writefile('set_password.html')
    
    def fn_chg_password(self):
        self.req.writefile('chg_password.html')
    
    def fn_load_dashboard(self):
        charts = []
        
        if False and self.user_lvl & (1 << config.USER_PERM_BIT['sales']):
            cr = self.get_customer_report()
            if cr:
                dps = []
                for k,v in cr['active_counts']: dps.append( {'x': k * 1000, 'y': v} );
                
                charts = [
                    {
                        'name': 'chart_active_customer_count',
                        'config': {
                            'zoomEnabled': True,
                            'theme': "theme2",
                            'title': {'text': "Active Customers"},
                            'axisX': {'valueFormatString': "MMM-YYYY", 'labelAngle': -50},
                            'data': [ {'type': "line", 'xValueType': "dateTime", 'dataPoints': dps} ]
                        }    
                    },
                ]
        
        
        self.req.writejs( {'charts': charts} )
     