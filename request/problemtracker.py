import config
import hashlib
import json
import time
import struct
import re


TICKET_TYPES = {

1: 'Low Stock',
2: 'Out Of Stock',
50: 'Wrong Information',

}

T_FLAG_APPROVED = 1 << 1
T_FLAG_CLOSED = 1 << 2


DEFAULT_PERM = (1 << config.USER_PERM_BIT['base access']) | (1 << config.USER_PERM_BIT['normal access'])
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        r = {
            'tab_cur_idx' : 2,
            'title': 'Problem Tracker',
            'tabs': [ ('report_a_problem', 'Item'), ]
        }
        self.req.writefile('tmpl_multitabs.html', r)

    def fn_report_a_problem(self):
        r = {
            'TICKET_TYPES': TICKET_TYPES
        }
        
        self.req.writefile('tracker/report_a_problem.html', r)


    def fn_get_ticket_hist(self):
        t_sid = self.req.psv_int('sid')
        t_id = self.req.psv_int('type')

        cur = self.cur()
        cur.execute('select * from tracker where sid=%s and type=%s order by id desc limit 6', (t_sid, t_id))
        ret = []
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            r['js'] = json.loads('[' + r['js'] + ']')

            if r['state'] & T_FLAG_APPROVED:
                r['state_s'] = 'Approved'
            elif r['state'] & T_FLAG_CLOSED:
                r['state_s'] = 'Closed'
            else:
                r['state_s'] = 'Pending'

            ret.append(r)

        self.req.writejs(ret)


    def fn_get_ticket_types_by_item(self):
        t_sid = self.req.psv_int('sid')

        cur = self.cur()

        ret = []
        for tid,tnz in TICKET_TYPES.items():
            cur.execute('select state from tracker where sid=%s and type=%s order by id desc limit 1', (t_sid, tid))
            rows = cur.fetchall()
            if rows:
                ret.append( (tid, tnz, rows[0][0]) )
            else:
                ret.append( (tid, tnz, None) )

        self.req.writejs(ret)
        
    def fn_new_ticket(self):
        t_type = self.req.psv_int('type')
        t_msg = self.req.psv_ustr('msg')
        t_sid = self.req.psv_int('sid')
        if not TICKET_TYPES.has_key(t_type): return

        cts = int(time.time())

        cur = self.cur()

        cur.execute('select id from tracker where sid=%s and state=0 and type=%s', (t_sid, t_type))
        rows = cur.fetchall()
        if rows:
            t_id = rows[0][0]
            t_js = json.dumps([self.user_id, self.user_name, None, t_msg or '* Report *', int(time.time())], separators=(',',':'))
            cur.execute("update tracker set mts=%s,js=concat(js, ',', %s) where id=%s and state=0", (
                cts, t_js, t_id
                )
            )
        else:
            t_js = json.dumps([self.user_id, self.user_name, None, t_msg, int(time.time())], separators=(',',':'))
            cur.execute('insert into tracker values(null,0,%s,%s,%s,%s)', (
                t_type, t_sid, t_js, cts
                )
            )
            t_id = cur.lastrowid

        self.req.writejs({'id' : t_id})

    def fn_close_ticket(self):
        t_id = self.req.psv_int('id')
        cur = self.cur()
        cur.execute("update tracker set state=-1 where id=%s", (
            t_id,
            )
        )
        rc = int(cur.rowcount <= 0)

        if not rc:
            cts = int(time.time())
            t_js = json.dumps([self.user_id, self.user_name, None, '* Closed *', int(time.time())], separators=(',',':'))
            cur.execute("update tracker set mts=%s,js=concat(js, ',', %s) where id=%s", (
                cts, t_js, t_id
                )
            )

        self.req.writejs({'err': rc})

    fn_close_ticket.PERM = 1 << config.USER_PERM_BIT['purchasing']

    def fn_reply_ticket(self):
        t_id = self.req.psv_int('id')
        t_msg = self.req.psv_ustr('msg')
        t_to_user_name = self.req.psv_ustr('to_user_name')
        if t_to_user_name == self.user_name: t_to_user_name = None
        if not t_msg: return

        t_js = json.dumps([self.user_id, self.user_name, t_to_user_name, t_msg, int(time.time())], separators=(',',':'))
        cts = int(time.time())
        cur = self.cur()
        cur.execute("update tracker set mts=%s,js=concat(js, ',', %s) where id=%s and state=0", (
            cts, t_js, t_id
            )
        )

        self.req.writejs({'err': int(cur.rowcount <= 0)})


    def fn_del_ticket(self):
        t_id = self.req.psv_int('id')

        cur = self.cur()
        cur.execute('delete from tracker where id=%s', (t_id, ))
        self.req.writejs({'err': int(cur.rowcount <= 0)})

    fn_del_ticket.PERM = 1 << config.USER_PERM_BIT['purchasing']

    def fn_get_tickets_by_item(self):
        sid = self.req.qsv_int('sid')
        direction = self.req.qsv_int('direction')
        if direction not in (1, -1): return
        a_token = json.loads(self.req.qsv_ustr('token') or '{}')
        rlen = min(max(self.req.qsv_int('len'), 10), 50)
        goto = self.req.qsv_int('hint')
        
        cur = self.cur()
        token = {}
        if not a_token:
            if goto:
                cur.execute('select * from tracker where sid=%d and id<=%d order by id desc limit 0,%d' % (
                    sid, goto, rlen,
                    )
                )
                lst = cur.fetchall()

                if len(lst) < rlen:
                    cur.execute('select * from tracker where sid=%d and id>%d order by id asc limit 0,%d' % (
                        sid, goto, rlen - len(lst),
                        )
                    )
                    x_lst = cur.fetchall()
                    x_lst.reverse()
                    lst[:0] = x_lst

            else:
                cur.execute('select * from tracker where sid=%d order by id desc limit 0,%d' % (
                    sid, rlen,
                    )
                )
                lst = cur.fetchall()
                
            if lst: token = {'t': lst[0][0], 'b': lst[-1][0]}
            
        else:
            token = {'t': int(a_token.get('t')), 'b': int(a_token.get('b'))}
            if direction == 1:
                cur.execute('select * from tracker where sid=%d and id<%d order by id desc limit 0,%d' % (
                    sid, token['b'], rlen,
                    )
                )
                lst = cur.fetchall()
                if lst: token['b'] = lst[-1][0]
                
            else:
                cur.execute('select * from tracker where sid=%d and id>%d order by id asc limit 0,%d' % (
                    sid, token['t'], rlen,
                    )
                )
                lst = cur.fetchall()
                lst.reverse()
                if lst: token['t'] = lst[0][0]
        
        _lst = lst
        lst = []
        for r in _lst:
            r = list(r)
            r[2] = TICKET_TYPES.get(r[2], 'UNK')
            lst.append(r)

        self.req.writejs({'token': json.dumps(token, separators=(',',':')), 'lst': lst})


    def fn_get_items(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        t_type = self.qsv_int('type')

        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            d_users = dict([f_v[:2] for f_v in self.getuserlist()])
            cur.execute('select SQL_CALC_FOUND_ROWS t.id,t.type,si.name,t.js,t.mts,t.sid,si.num from tracker t left join sync_items si on (t.sid=si.sid) where t.state=0'+(t_type and ' and t.type='+str(t_type) or '')+' order by id desc limit %d,%d' % (
                        sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                r = list(r)
                r[1] = TICKET_TYPES.get(r[1], 'UNK')
                r[2] = '%d - %s' % (r[6], r[2])
                r[4] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(r[4]))
                r[5] = str(r[5])

                lr = json.loads('[' + r[3] + ']')[-1]
                r[3] = lr[3] and '%s: %s' % (lr[1], lr[3]) or ''

                apg.append(r)

            cur.execute('select FOUND_ROWS()')

        else:
        
            cur.execute('select count(*) from tracker where state=0'+(t_type and ' and type='+str(t_type) or ''))

        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
        
        