import config
import hashlib
import os
import json
import inspect

CFG = {
    'id': 'user_AF5643BB',
    'name': 'User',
    'perm_list': [
    ('access', ''),
    ]
}

class RequestHandler(App.load('/basehandler').RequestHandler):

    def fn_default(self):

        tabs = [{'id': 'role', 'name': 'Role'}, {'id': 'user', 'name': 'User'}, {'id': 'app', 'name': 'App'}]
        r = {
            'tab_cur_idx' : 2,
            'title': 'Permission',
            'tabs': tabs
        }
        self.req.writefile('tmpl_multitabs_v2.html', r)

    def fn_get_role_perms(self):
        role_id = self.qsv_int('role_id')
        cur = self.cur()
        cur.execute('select role_perms from user_role where role_id=%s', (role_id, ))
        rows = cur.fetchall()
        role_perms = {}
        if rows: role_perms = rows[0][0] and json.loads(rows[0][0]) or {}

        rm = dict([ (f_x[1], f_x[0]) for f_x in config.BASE_ROLES_MAP.items() ])
        self.req.writejs({'role_id': role_id, 'role_name': rm.get(role_id), 'role_perms': role_perms})

    def fn_save_role(self):
        role_id,role_perms = self.req.psv_js('js')

        role_id = int(role_id)
        if role_id not in config.BASE_ROLES_MAP.values(): return

        ids = set([f_x[0]['id'] for f_x in self.get_app_lst()])
        role_perms = dict([(pi, int(pv) & 0x7FFFFFFF) for pi,pv in role_perms.items() if pi and pi in ids])

        cur = self.cur()
        cur.execute('replace into user_role values(%s,%s)', (
            role_id, json.dumps(role_perms, separators=(',',':'))
            )
        )
        self.req.writejs({'role_id': role_id})

    def fn_role(self):
        role_list = config.BASE_ROLES_MAP.items()
        role_list.sort(key=lambda f_x: f_x[1])

        d = {'role_list': role_list, 'cfgs': self.get_app_lst()}
        self.req.writefile('user_role.html', d)

    def fn_get_user_roles(self):
        user_id = self.qsv_int('user_id')
        cur = self.cur()
        cur.execute('select user_roles from user where user_id=%s', (user_id,))
        user_roles = cur.fetchall()[0][0]

        self.req.writejs({'user_roles': user_roles, 'user_id': user_id})

    def fn_set_user_roles(self):
        user_id = self.req.psv_int('user_id')
        roles = self.req.psv_int('roles') & config.BASE_ROLES_MAP_MASK

        cur = self.cur()
        cur.execute('update user set user_roles=%s where user_id=%s', (roles, user_id))

        self.req.writejs({'user_id': user_id, 'roles':config.BASE_ROLES_MAP_MASK})

    def fn_save_user_perms(self):
        user_id,user_perms = self.req.psv_js('js')
        user_id = int(user_id)
        if not user_id: return

        ids = set([f_x[0]['id'] for f_x in self.get_app_lst()])
        user_perms = dict([(pi, int(pv) & 0x7FFFFFFF) for pi,pv in user_perms if pi and pi in ids])

        cur = self.cur()
        cur.execute('update user set user_perms=%s where user_id=%s', (
            user_perms and json.dumps(user_perms, separators=(',',':')) or None, user_id
            )
        )
        self.req.writejs({'user_id': user_id})

    def fn_get_user_perms(self):
        user_id = self.qsv_int('user_id')
        cur = self.cur()
        cur.execute('select user_roles,user_perms,user_name from user where user_id=%s', (user_id, ))
        rows = cur.fetchall()

        user_perms = {}
        role_perms = {}
        user_name = None

        if rows:
            user_roles,user_perms,user_name = rows[0]
            user_perms = user_perms and json.loads(user_perms) or {}
            user_roles = config.extract_bits(user_roles)

            if user_roles:
                cur.execute('select role_perms from user_role where role_id in (%s)' % (
                    ','.join(map(str, user_roles)),
                    )
                )
                for r in cur.fetchall():
                    if not r[0]: continue
                    p = json.loads(r[0])
                    for k,v in p.items(): role_perms[k] = role_perms.get(k, 0) | v


        perms = role_perms.copy()
        perms.update(user_perms)

        role_list = config.BASE_ROLES_MAP.items()
        role_list.sort(key=lambda f_x: f_x[1])

        roles_s = ', '.join([ r[0] for r in role_list if r[1] in user_roles ])

        self.req.writejs({'user_id': user_id, 'user_perms': user_perms, 'role_perms': role_perms, 'merg_perms': perms,
            'roles_s': roles_s, 'user_name': user_name})

    def fn_user(self):
        role_list = config.BASE_ROLES_MAP.items()
        role_list.sort(key=lambda f_x: f_x[1])

        d = {'role_list': role_list, 'cfgs': self.get_app_lst()}
        self.req.writefile('user_v3.html', d)

    def fn_get_user_list(self):
        ret = {'res':{'len':0, 'apg':[]}}

        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select user_id,user_name,user_roles from user order by user_id desc limit %d,%d' % (
                sidx * pgsz, (eidx - sidx) * pgsz
                )
            )
            nzs = cur.column_names
            for r in cur:
                r = list(r)
                r[2] = '%08x' % r[2]
                apg.append(r)

        cur.execute('select count(*) from user')
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)

    def fn_add_user(self):
        user_name = self.req.psv_ustr('name').strip().lower()
        if not user_name: return

        cur = self.cur()

        dpw = self.genpasswd('')
        cur.execute("insert into user values (0,%s,%s,0,0,0,null)", (user_name, dpw))
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
    
    

    def get_apps_fns(self):
        cfgs = []
        for cfg,md,nz in self.get_app_lst():
            fns = []
            rh = md.RequestHandler
            for x in inspect.getmembers(rh):
                if x[0][:3] == 'fn_' and x[0].replace('_', '').isalnum() and inspect.ismethod(x[1]) and \
                x[1].im_func.func_globals['RequestHandler'] == rh:
                    fns.append(x[0][3:])

            cfgs.append( (cfg, nz, fns) )

        return cfgs


    def fn_app(self):
        role_list = config.BASE_ROLES_MAP.items()
        role_list.sort(key=lambda f_x: f_x[1])
        d = {'role_list': role_list, 'cfgs': self.get_apps_fns()}
        self.req.writefile('user_app.html', d)



    def fn_get_apps_cfg(self):
        self.req.writejs(self.get_config_js('APPS_BY_DEPTS', []))

    def fn_set_apps_cfg(self):
        js = self.req.psv_js('js')
        da = dict([(f_v[1], set(f_v[2])) for f_v in self.get_apps_fns()])

        njs = []
        for dept in js:
            name = dept.get('name') or ''
            apps = []
            for app in dept.get('apps'):
                md = app.get('md')
                if md not in da: continue
                fn = app.get('fn')
                if fn not in da[md]: continue
                apps.append( {'name':app.get('name') or '', 'md':md, 'fn':fn} )

            njs.append( {'name':name, 'apps':apps} )

        self.set_config_js('APPS_BY_DEPTS', njs)
        self.req.writejs( {'ret': 0} )


