import time
import config


PERM_ADMIN = 1 << config.USER_PERM_BIT['admin']
PERM_TIME = 1 << config.USER_PERM_BIT['time']
PERM_ITEM_STAT_ACCESS = 1 << config.USER_PERM_BIT['item stat access']
PERM_NORMAL_ACCESS = 1 << config.USER_PERM_BIT['normal access']

TOOLS_MAP = (

('Admin', (
    ('Commision', 'comm', PERM_ADMIN),
    ('Comm By Dept', 'comm?fn=comm_by_dept', PERM_ADMIN),
    ('User', 'user', PERM_ADMIN),
    ('ItemSale', 'reportitem', PERM_ADMIN),
    ('Project', 'sys?fn=project', PERM_ADMIN),
    #('Mac', 'sys?fn=mac', PERM_ADMIN),
)),

('HR', (
    ('TimeMGR', 'clockinv2?fn=mgr', PERM_TIME),
)),


('Accounting', (
)),

('Purchasing', (
    ('ItemSold', 'itemsold', PERM_ITEM_STAT_ACCESS),
)),

('Sales', (
    ('History', 'hist', PERM_NORMAL_ACCESS),
    ('Error', 'fixup', PERM_NORMAL_ACCESS),
)),

('Warehouse', (
    ('Label', 'label', PERM_NORMAL_ACCESS),
    ('Delivery', 'delivery', PERM_NORMAL_ACCESS),
)),

)



DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
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
        