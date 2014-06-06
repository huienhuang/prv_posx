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
        msg = json.dumps([self.user_id, self.user_name, '', int(time.time()), 0], separators=(',',':'))
        
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
        
        self.req.writejs({'err':int(rc <= 0)})
    
    def fn_approve(self):
        p_id = self.req.psv_int('p_id')
        deadline = self.req.psv_ustr('deadline')
        
        deadline_ts = 0
        if deadline:
            m_yr,m_mon,m_day = map(int, deadline.split('-', 3))
            deadline_ts = int(time.mktime(datetime.date(m_yr, m_mon, m_day).timetuple()))
        
        msg = json.dumps([self.user_id, self.user_name, 'Approved', int(time.time()), 0], separators=(',',':'))
        
        cur = self.cur()
        cur.execute("update project set p_state=%s,p_approved_by_uid=%s,p_deadline_ts=%s,p_msg=concat(p_msg,',',%s) where p_id=%s and p_state<%s", (
            P_STATES['approved'], self.user_id, deadline_ts, msg, p_id, P_STATES['approved']
            )
        )
        rc = cur.rowcount
        
        self.req.writejs({'err':int(rc <= 0)})
    
    fn_approve.PERM = 1 << config.USER_PERM_BIT['admin']
    
    def fn_setprogress(self):
        p_id = self.req.psv_int('p_id')
        p_percent = self.req.psv_int('percent')
        if not p_id or p_percent < 0 or p_percent > 100: return
        
        cts = int(time.time())
        
        cur = self.cur()
        if p_percent == 100:
            msg = json.dumps([self.user_id, self.user_name, 'Completed', cts, 0], separators=(',',':'))
            cur.execute("update project set p_state=%s,p_progress=100,p_completion_ts=%s,p_msg=concat(p_msg,',',%s) where p_id=%s and p_state>=%s and p_state<%s", (
                P_STATES['completed'], cts, msg, p_id, P_STATES['approved'], P_STATES['completed']
            ))
        else:
            msg = json.dumps([self.user_id, self.user_name, 'In progress: %d%%' % (p_percent,), int(time.time()), 0], separators=(',',':'))
            cur.execute("update project set p_state=%s,p_progress=%s,p_beginning_ts=if(p_beginning_ts,p_beginning_ts,%s),p_msg=concat(p_msg,',',%s) where p_id=%s and p_state>=%s and p_state<%s", (
                P_STATES['in progress'], p_percent, cts, msg, p_id, P_STATES['approved'], P_STATES['completed']
            ))
        
        rc = cur.rowcount
        
        self.req.writejs({'err':int(rc <= 0)})
        
    def fn_add_msg(self):
        p_id = self.req.psv_int('p_id')
        val = self.req.psv_ustr('val')[:512].strip()
        if not p_id or not val: return
        
        msg = json.dumps([self.user_id, self.user_name, val, int(time.time()), 1], separators=(',',':'))
        
        cur = self.cur()
        cur.execute("update project set p_msg=concat(p_msg,',',%s) where p_id=%s", (
            msg, p_id
            )
        )
        rc = cur.rowcount
        
        self.req.writejs({'err': int(rc <= 0)})
        
    
    def fn_get_msg(self):
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
        
        msgs = json.loads('['+r['p_msg']+']')
        k = 0
        for m in msgs:
            m.insert(0, k)
            k += 1
            
        mms = [
            r['p_name'], r['p_desc'],
            '- state: ' + P_STATES_R.get(r['p_state']),
        ]
        if r['p_state'] >= P_STATES['approved']:
            if r['p_deadline_ts']: mms.append( '- deadline ' + time.strftime("%m/%d/%Y", time.localtime(r['p_deadline_ts'])) )
            
            a_user = self.finduser(r['p_approved_by_uid'])
            mms.append('- approved by ' + (a_user and a_user[1] or 'UNK'))
        
        if r['p_state'] >= P_STATES['in progress']:
            if r['p_state'] == P_STATES['in progress']:
                mms.append( '- in progress: %d%%' % (r['p_progress'],))
                
            mms.append( '- beginning date: ' + time.strftime("%m/%d/%Y", time.localtime(r['p_beginning_ts'])) )
            
            if r['p_state'] == P_STATES['completed']:
                mms.append( '- completion date: ' + time.strftime("%m/%d/%Y", time.localtime(r['p_completion_ts'])) )
        
        msgs[0][3] = '\n'.join(mms)
        
        token = {}
        if not a_token:
            lst = None
            msgs.reverse()
            if goto:
                idx = len(msgs) - 1 - goto
                lst = msgs[ idx : idx + rlen ]
            if not lst: lst = msgs[ 0 : rlen ]
            if lst: token = {'t': lst[0][0], 'b': lst[-1][0]}
            
        else:
            token = {'t': int(a_token.get('t')), 'b': int(a_token.get('b'))}
            if direction == 1:
                msgs.reverse()
                idx = len(msgs) - token['b']
                lst = msgs[ idx : idx + rlen ]
                if lst: token['b'] = lst[-1][0]
                
            else:
                idx = token['t'] + 1
                lst = msgs[ idx : idx + rlen ]
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
                    '%d%%' % (p_progress,),
                    p_deadline_ts and time.strftime("%m/%d/%Y", time.localtime(p_deadline_ts)) or '',
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
        
        
        