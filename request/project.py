import json
import time
import config
import datetime


P_STATES = {
'pending' : 0,
'approved' : 32,
'in progress' : 64,
'completed' : 128,
}

P_STATES_R = dict([(f_v,f_k) for f_k,f_v in P_STATES.items()])


DEFAULT_PERM = 1 << config.USER_PERM_BIT['sys']
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('project.html', {'P_STATES': P_STATES})

    def fn_view(self):
        r = {
            'p_id': self.qsv_int('p_id'),
            'P_STATES': P_STATES
        }
        self.req.writefile('project_view.html', r)
    
    def fn_new(self):
        name = self.req.psv_ustr('name')
        desc = self.req.psv_ustr('desc')
        msg = json.dumps([self.user_id, self.user_name, 0, '', '', int(time.time()), 0], separators=(',',':'))
        
        cur = self.cur()
        cur.execute("insert into project values(null,0,0,%s,0,%s,%s,0,0,0,%s)", (
            self.user_id, name, desc, msg
            )
        )
        
        self.req.writejs({'rid': cur.lastrowid})
    
    def fn_delete(self):
        p_id = self.req.psv_int('p_id')
        cur = self.cur()
        cur.execute('delete from project where p_id=%s and p_state<%s', (p_id, P_STATES['completed']))
        rc = cur.rowcount
        
        self.req.writejs({'err':int(not rc)})
    
    def fn_approve(self):
        p_id = self.req.psv_int('p_id')
        msg = json.dumps([self.user_id, self.user_name, 0, '', 'Approved', int(time.time()), 0], separators=(',',':'))
        
        cur = self.cur()
        cur.execute("update project set p_state=%s,p_msg=concat(p_msg,',',%s) where p_id=%s and p_state<%s", (
            P_STATES['approved'], msg, p_id, P_STATES['approved']
            )
        )
        rc = cur.rowcount
        
        self.req.writejs({'err':int(not rc)})
    
    def fn_msg(self):
        p_id = self.req.qsv_int('p_id')
        direction = self.req.qsv_int('direction')
        if direction not in (1, -1): return
        a_token = json.loads(self.req.qsv_ustr('token') or '{}')
        rlen = min(max(self.req.qsv_int('len'), 10), 50)
        goto = self.req.qsv_int('hint')
        
        cur = self.cur()
        cur.execute('select * from project where p_id=%s', (p_id,))
        nzs = cur.column_names
        r = cur.fetchall()
        if not r: return
        r = dict(zip(nzs, r[0]))
        
        msgs = json.loads(r['p_msg'])
        msg[0][4] = 'Created'
        
        token = {}
        if not a_token:
            lst = None
            msgs = reversed(msgs)
            if goto: lst = msgs[goto:goto-rlen]
            if not lst: lst = msgs[-1:goto-rlen]
                
            if lst: token = {'t': lst[0][0], 'b': lst[-1][0]}
            
        else:
            token = {'t': int(a_token.get('t')), 'b': int(a_token.get('b'))}
            if direction == 1:
                cur.execute('select id,js from customer_comment where cid=%d and id<%d order by id desc limit 0,%d' % (
                    cid, token['b'], rlen,
                    )
                )
                lst = cur.fetchall()
                if lst: token['b'] = lst[-1][0]
                
            else:
                cur.execute('select id,js from customer_comment where cid=%d and id>%d order by id asc limit 0,%d' % (
                    cid, token['t'], rlen,
                    )
                )
                lst = cur.fetchall()
                lst.reverse()
                if lst: token['t'] = lst[0][0]
        
        self.req.writejs({'token': json.dumps(token, separators=(',',':')), 'lst': lst})
    
    def fn_get(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        state = self.qsv_int('state')
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            users = dict([(v[0], v[1])for v in self.getuserlist()])
            
            cur.execute('select SQL_CALC_FOUND_ROWS p_id,p_state,p_progress,p_created_by_uid,p_approved_by_uid,p_name,p_desc,p_deadline_ts,p_beginning_ts,p_completion_ts from project where p_state=%d order by p_id desc limit %d,%d' % (
                        state, sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                p_id,p_state,p_progress,p_created_by_uid,p_approved_by_uid,p_name,p_desc,p_deadline_ts,p_beginning_ts,p_completion_ts = r
                
                apg.append((
                    p_id,
                    p_name +' - '+ p_desc,
                    P_STATES_R[p_state],
                    '%%%d' % (p_progress,),
                    p_deadline_ts and time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(p_deadline_ts)) or '',
                    p_beginning_ts and time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(p_beginning_ts)) or '',
                    p_completion_ts and time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(p_completion_ts)) or '',
                    users.get(p_created_by_uid, 'UNK'),
                    users.get(p_approved_by_uid, 'UNK'),
                    p_state
                    )
                )
                
            cur.execute('select FOUND_ROWS()')
        else:
            cur.execute('select count(*) from project where p_state=%d' % (
                state,
                )
            )
        
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
        
        
        