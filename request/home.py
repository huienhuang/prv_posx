import time
import config

DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        
        d = {'user_lvl': self.user_lvl,
             'user_name': self.user_name,
             'user_id': self.user_id,
             'PERM_BIT': config.USER_PERM_BIT
             }
        self.req.writefile('home.html', d)
        
    def fn_password(self):
        old_passwd = self.req.psv_ustr('old_passwd', '')
        new_passwd = self.req.psv_ustr('new_passwd', '')
        self.req.writejs( {'res': int(self.updpasswd(old_passwd, new_passwd))} )
        
    
    def fn_env(self):
        self.req.writefile('env.html', {'env':self.environ})
    