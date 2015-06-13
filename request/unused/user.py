import config
import hashlib


DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/basehandler').RequestHandler):

    def fn_default(self):
        d = {'userlist': self.getuserlist(), 'PERM_BIT': config.USER_PERM_BIT}
        self.req.writefile('user_v2.html', d)
    
    def fn_add_user(self):
        user_name = self.req.psv_ustr('name').strip().lower()
        if not user_name: return
        
        db = self.db()
        cur = db.cur()
        
        cur.execute('select count(*) from user where user_name=%s', (user_name,))
        if cur.fetchall()[0][0] > 0: self.req.exitjs({'uid':0, 'err':'user exists'})
        
        dpw = self.genpasswd('')
        cur.execute("insert into user values (0,%s,%s,0,0)", (user_name, dpw))
        self.req.writejs({'uid': cur.lastrowid})
    
    def fn_set_password(self):
        user_id = self.req.psv_int('uid')
        password = self.req.psv_ustr('password').strip()
        
        if user_id <= 1: return
        
        db = self.db()
        cur = db.cur()
        
        dpw = self.genpasswd(password)
        cur.execute('update user set user_passwd=%s where user_id=%s', (dpw, user_id))
        
        self.req.writejs({'uid': user_id})

    def fn_set_name(self):
        user_id = self.req.psv_int('uid')
        name = self.req.psv_ustr('name').strip()
        
        if user_id <= 1 or not name: return
        
        db = self.db()
        cur = db.cur()
        
        cur.execute('update user set user_name=%s where user_id=%s', (name, user_id))
        
        self.req.writejs({'uid': user_id})
        
    def fn_set_perm(self):
        user_id = self.req.psv_int('uid')
        perm = self.req.psv_int('perm')
        
        if user_id <= 1 or perm < 0: return
        
        perm_v = 0
        for v in config.USER_PERM_BIT.values(): perm_v |= perm & (1 << v)
        perm_v &= (1 << 31) - 1 #no admin allowed
        
        db = self.db()
        cur = db.cur()
        
        cur.execute('update user set user_lvl=%s where user_id=%s', (perm_v, user_id))
        
        self.req.writejs({'uid': user_id})

    def fn_del_user(self):
        user_id = self.req.psv_int('uid')
        
        ret = 0
        if user_id > 1:
            db = self.db()
            cur = db.cur()
            cur.execute('delete from user where user_id=%s' % (user_id,))
            if cur.rowcount > 0: ret = 1
            
        self.req.writejs({'ret':ret})
    
    