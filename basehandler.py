import hashlib
import time
import winlib
import bisect
import struct
import tinywsgi2
import config
import dbref
import urllib
import urlparse

LOGIN_PERM = (1 << config.USER_PERM_BIT['base access']) | (1 << config.USER_PERM_BIT['normal access'])
ADMIN_PERM = 1 << config.USER_PERM_BIT['admin']

DEFAULT_PERM = ADMIN_PERM
class RequestHandler(tinywsgi2.RequestHandler):
    
    def setup(self):
        tinywsgi2.RequestHandler.setup(self)
        
        self.environ = self.req.environ
        self.cookie = self.req.cookie
        self.out_cookie = self.req.out_cookie
        
        self.user_id = 0
        self.user_name = None
        self.user_lvl = 0
        self.__db = None
        
        self.is_ajax = bool(self.qsv_int('ajax'))
    
    def cleanup(self):
        tinywsgi2.RequestHandler.cleanup(self)
        
        if self.__db != None: dbref.put(self.req)
        self.__db = None
        
    def db(self):
        if self.__db != None: return self.__db
        self.__db = dbref.get(self.req)
        return self.__db
    
    def cur(self):
        return self.db().cur()

    def check_mac(self, cur_mac=[]):
        rip = config.ip2ulong( self.environ.get('REMOTE_ADDR') )
        if rip == 0x0100007F or rip == config.server_network[0]: return True
        if (rip & config.server_network[1]) != config.server_network[2]: return False
        
        m = self.getconfigv2('allowed_mac_addrs', '')
        if not m: return False
        a = struct.unpack('<' + 'Q' * (len(m) / 8), m)
        
        res = winlib.get_phy_addr(rip)
        if res[0] <= 0 or not res[1]: return False
        
        i = bisect.bisect_left(a, res[1])
        if i >= len(a) or a[i] != res[1]: return False
        
        cur_mac.append(res[1])
        return True
        
    def check_mac_v2(self):
        rip = self.environ.get('REMOTE_ADDR', '')
        ips = map(int, rip.split('.'))
        if ips == [127, 0, 0, 1]: return True
        if ips[:3] != list(config.local_network[:3]): return False
        cur = self.db().cur()
        cur.execute('select mac from ipmac where ip=%d and uts>=%d' % (
            ips[3], int(time.time()) - 2
            )
        )
        r = cur.fetchall()
        if not r: return True
        
        cur_mac = r[0][0]
        mac_addrs = self.getconfigv2('allowed_mac_addrs')
        if mac_addrs:
            macs = mac_addrs.split(',')
            for mac in macs:
                if not mac: continue
                if mac == cur_mac: return True
        
        return False
    
    def logout(self):
        self.out_cookie['__auth__'] = ''
        self.out_cookie['__auth__']['expires'] = -(3600 * 24)
    
    def login(self, in_uid=None, in_pass=None):
        rip = self.environ.get('REMOTE_ADDR', '')
        auth = self.cookie.get('__auth__')
        ts_idx = int(int(time.time()) / 3600)
        
        uid = None
        if in_uid == None:
            #check cookie auth
            auth_ = (auth and auth.value or '').split(':')
            if len(auth_) == 2 and auth_[0].isdigit():
                uid = int(auth_[0])
                aid = auth_[1]
        else:
            #check user input
            uid = in_uid
            aid_ = self.gen_pre_auth(rip, uid, self.genpasswd(in_pass))
            aid = self.gen_auth(aid_, ts_idx - 1)
            
            self.out_cookie['__uid__'] = str(uid)
            self.out_cookie['__uid__']['expires'] = 3600 * 24 * 360
            
            
        if uid:
            cur = self.cur()
            cur.execute('select user_name,user_passwd,user_lvl from user where user_id=%d limit 1' % (uid, ))
            r = cur.fetchall()
            r = r and r[0] or None
            if r:
                r_aid_ = self.gen_pre_auth(rip, uid, r[1])
                r_aid = self.gen_auth(r_aid_, ts_idx)
                
                login_pass = 0
                if r_aid == aid:
                    login_pass = 1
                else:
                    r_aid_prev = self.gen_auth(r_aid_, ts_idx - 1)
                    if r_aid_prev == aid:
                        login_pass = 2
                    
                if login_pass:
                    self.user_id = uid
                    self.user_name = r[0]
                    self.user_lvl = int(r[2])
                    
                    if login_pass == 2: self.out_cookie['__auth__'] = '%s:%s' % (uid, r_aid)
                    if in_uid and not in_pass: self.req.redirect('home?fn=set_password')
                    
                    return True
        
        self.user_id = 0
        self.user_name = None
        self.user_lvl = 0
        
        if auth: self.logout()
        
        return False
    
    
    def get_perm_lvl(self, fn_nz, fn_inst):
        return getattr(fn_inst, 'PERM', fn_inst.im_func.func_globals.get('DEFAULT_PERM', DEFAULT_PERM))
        
    def check_perm(self, fn_nz, fn_inst):
        rlvl = self.get_perm_lvl(fn_nz, fn_inst)
        if not rlvl: return True
        
        cur_mac = []
        if not self.check_mac(cur_mac): return False
        if cur_mac:
            if rlvl & ADMIN_PERM:
                macs = config.settings.get('macs_admin')
                if macs and cur_mac[0] not in macs: return False
        
        self.login()
        if self.user_id and self.user_lvl & rlvl:
            return True
        elif self.is_ajax:
            self.req.exitjs({'err':-999})
            return False
        else:
            self.req.redirect('?' + urllib.urlencode({'fn': 'login', 'req_qs': self.environ.get('QUERY_STRING') or ''}))
            return False
    
    def genpasswd(self, s):
        return hashlib.md5('%s%s' % (config.passwd_code, s)).hexdigest()
    
    def gen_pre_auth(self, rip, uid, dpw):
        return hashlib.md5('%s%s%s%s' % (rip, config.secret_code, uid, dpw)).digest()
    
    def gen_auth(self, pre_auth, ts_idx):
        return hashlib.md5('%s%s%s' % (pre_auth, config.secret_code_v1, ts_idx)).hexdigest()
    
    def updpasswd(self, old, new):
        old_dpw = self.genpasswd(old)
        new_dpw = self.genpasswd(new)
        db = self.db()
        cur = db.cur()
        cur.execute("update user set user_passwd=%s where user_id=%s and user_passwd=%s limit 1", (
            new_dpw, self.user_id, old_dpw
        ))
        rowcount = cur.rowcount
        db.commit()
        return rowcount > 0
    
    def getuserlist(self):
        cur = self.db().cur()
        cur.execute('select user_id,user_name,user_lvl from user order by user_id asc')
        return cur.fetchall()
    
    def finduser(self, uid):
        cur = self.cur()
        cur.execute('select user_id,user_name,user_lvl from user where user_id=%s limit 1', (uid,))
        res = cur.fetchall()
        return res and res[0] or None
    
    def get_user_by_name(self, user_name):
        cur = self.cur()
        cur.execute('select user_id,user_name,user_lvl from user where user_name=%s limit 1', (user_name,))
        res = cur.fetchall()
        return res and res[0] or None
    
    def fn_getusers(self):
        users = [ user for user in self.getuserlist() if user[2] & LOGIN_PERM ]
        self.req.writejs(users)
    #fn_getusers
    fn_getusers.PERM = 0
    
    def fn_getuser(self):
        self.login()
        self.req.writejs({'user_id': self.user_id})
    #fn_getuser
    fn_getuser.PERM = 0
    
    def fn_login_js(self):
        ret = {'user_id':0}
        user_id = self.req.psv_ustr('user_id')
        user_pass = self.req.psv_ustr('user_passwd')
        user_id = user_id.isdigit() and int(user_id) or 0
        if user_id and self.login(user_id, user_pass): ret['user_id'] = self.user_id
        
        self.req.writejs(ret)
    #fn_login_js
    fn_login_js.PERM = 0
        
    def fn_login(self):
        req_qs = self.qsv_str('req_qs')
        
        user_id = self.req.psv_int('user_id')
        if user_id:
            user_pass = self.req.psv_ustr('user_passwd')
            if self.login(user_id, user_pass):
                qsl = [(f_k, f_v[0]) for f_k,f_v in urlparse.parse_qs(req_qs, keep_blank_values=True).items()]
                self.req.redirect('?' + urllib.urlencode(qsl, True))
                return False
        
        ck_uid = self.out_cookie.get('__uid__') or self.cookie.get('__uid__')
        ck_uid = unicode(ck_uid and ck_uid.value or '')
        ck_uid = ck_uid.isdigit() and int(ck_uid) or 0
        d = {
            'action_url': urllib.urlencode({'fn': 'login', 'req_qs': req_qs}),
            'ck_uid': ck_uid,
            'userlist': [ user for user in self.getuserlist() if user[2] & LOGIN_PERM ],
        }
        self.req.writefile('login.html', d)
    #fn_login
    fn_login.PERM = 0
    
    def fn_login_by_name_js(self):
        ret = {'user_id':0}
        user_name = self.req.psv_ustr('user_name')
        user_pass = self.req.psv_ustr('user_passwd')
        if not user_name: self.req.exitjs(ret)
        
        user = self.get_user_by_name(user_name)
        if not user: self.req.exitjs(ret)
        
        if not self.login(user[0], user_pass): self.req.exitjs(ret)
        
        ret['user_id'] = self.user_id
        self.req.writejs(ret)
    #fn_login_by_name_js
    fn_login_by_name_js.PERM = 0
    
    def fn_logout(self):
        self.logout()
        self.req.redirect('?fn=login')
        
        return False
    #fn_logout
    fn_logout.PERM = 0

    def qsv_int(self, k, dv=0):
        return self.req.qsv_int(k, dv)
        
    def qsv_str(self, k, dv=''):
        return self.req.qsv_ustr(k, dv)

    def getconfig(self, k, dv=0):
        return config.get_config(self.db(), k, dv)
    
    def setconfig(self, k, v):
        config.set_config(self.db(), k, v)
    
    def getconfigv2(self, k, dv=''):
        return config.get_configv2(self.db(), k, dv)
    
    def setconfigv2(self, k, v):
        config.set_configv2(self.db(), k, v)
