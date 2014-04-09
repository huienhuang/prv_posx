import time
import config


PERM_ADMIN = 1 << config.USER_PERM_BIT['admin']
PERM_TIME = 1 << config.USER_PERM_BIT['time']
PERM_ITEM_STAT_ACCESS = 1 << config.USER_PERM_BIT['item stat access']
PERM_NORMAL_ACCESS = 1 << config.USER_PERM_BIT['normal access']
PERM_BASE_ACCESS = 1 << config.USER_PERM_BIT['base access']

TOOLS_MAP = (

('Admin', (
    ('User', 'user', PERM_ADMIN),
    ('Project', 'sys?fn=project', PERM_ADMIN),
    #('Mac', 'sys?fn=mac', PERM_ADMIN),
)),

('Report', (
#    ('Commision', 'comm', PERM_ADMIN),
    ('Commision', 'comm?fn=comm_by_dept', PERM_ADMIN),
    ('Item Sale', 'reportitem', PERM_ADMIN),
    ('General Report', 'reportgeneral', PERM_ADMIN),
)),

('HR', (
    ('Time MGR', 'clockinv2?fn=mgr', PERM_TIME),
    ('PayRoll', '', PERM_TIME),
    ('PDT Tracking', '', PERM_TIME),
    ('Employee File', '', PERM_TIME),
    ('HR Metrics', '', PERM_TIME),
)),

('Accounting', (
)),

('Purchasing', (
    ('Item Sold', 'itemsold', PERM_ITEM_STAT_ACCESS),
    ('Label', 'label', PERM_BASE_ACCESS | PERM_NORMAL_ACCESS),
    ('Out Of Stock', '', PERM_NORMAL_ACCESS),
    ('Cycle Count', '', PERM_NORMAL_ACCESS),
    ('Receiving Schedule', '', PERM_NORMAL_ACCESS),
)),

('Sales', (
    ('History', 'hist', PERM_NORMAL_ACCESS),
    ('Error', 'fixup', PERM_NORMAL_ACCESS),
)),

('Warehouse', (
    ('Delivery', 'delivery', PERM_NORMAL_ACCESS),
    ('Pallet Map', '', PERM_NORMAL_ACCESS),
    ('Warehouse Map', '', PERM_NORMAL_ACCESS),
)),

)



DEFAULT_PERM = PERM_BASE_ACCESS | PERM_NORMAL_ACCESS
class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        tools_map_f = []
        for s_dept,l_tools in TOOLS_MAP:
            l_tools_f = []
            for tool in l_tools:
                if tool[2] and not (tool[2] & self.user_lvl): continue
                l_tools_f.append(tool)
            if l_tools_f: tools_map_f.append( (s_dept, l_tools_f) )
        
        d = {
            'user_lvl': self.user_lvl,
            'user_name': self.user_name,
            'user_id': self.user_id,
            'tools_map': tools_map_f
        }
        
        self.req.writefile('home.html', d)
        
    def fn_password(self):
        old_passwd = self.req.psv_ustr('old_passwd', '')
        new_passwd = self.req.psv_ustr('new_passwd', '')
        self.req.writejs( {'res': int(self.updpasswd(old_passwd, new_passwd))} )
        
    
    def fn_env(self):
        self.req.writefile('env.html', {'env':self.environ})
    
    
    def fn_set_password(self):
        self.req.writefile('set_password.html')
    
    
    def fn_load_dashboard(self):
        charts = []
        if self.user_lvl & (1 << config.USER_PERM_BIT['sales']):
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
     