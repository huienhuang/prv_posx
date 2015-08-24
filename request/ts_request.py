import config
import hashlib
import bisect
import time
import json

CFG = {
    'id': 'TS_REQUEST_C0000001',
    'name': 'Request',
    'perm_list': [
    ('access', ''),
    ('admin', ''),
    ]
}

PERM_ADMIN = 1 << 1

class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        tabs = [
        
        {'id': 'Request', 'name': 'Request'},
        {'id': 'View', 'name': 'View', 'src': '?fn=View'},
        {'id': 'pohelper', 'name': 'PO Helper', 'src': 'pohelper'},
        {'id': 'itemsold', 'name': 'Item Sold', 'src': 'itemsold'},

        ]
        r = {
            'tab_cur_idx' : 2,
            'title': 'Request',
            'tabs': tabs
        }
        self.req.writefile('tmpl_multitabs_v2.html', r)


    def fn_request(self):
        self.req.writefile('purchasing/ts_list.html')
        
    def fn_view(self):
        cur = self.cur()
        cur.execute('select id,nz from report where type=1 order by id desc')
        profiles = cur.fetchall()
        r = {
            'profiles': sorted(profiles, key=lambda f_x:f_x[1].lower())
        }
        self.req.writefile('purchasing/ts_request.html', r)
        
    
    def fn_get_lst(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        r_flg = 2

        ws = ['t.flg&2!=0']
        flg = self.qsv_int('flg')
        if flg == 1:
            ws.append('t.flg&1=0')
        elif flg == 2:
            ws.append('t.flg&1!=0')
        ws = ' and '.join(ws)

        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)

        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            d_users = dict([f_v[:2] for f_v in self.getuserlist()])
            cur.execute('select SQL_CALC_FOUND_ROWS t.*,q.state,q.errno,q.doc_num from inv_request t left join qbpos q on (t.qbpos_id=q.id) where %s order by pid desc limit %d,%d' % (
                        ws, sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            nzs = cur.column_names
            for r in cur:
                r = dict(zip(nzs, r))

                sts = 'Pending'
                if r['flg'] & 1:
                    sts = 'Transfering'
                    if r['state'] == 2:
                        if not r['errno']:
                            sts = 'Transfered'
                        else:
                            sts = 'Error'

                if r['dtype'] == 1:
                    dtype = 'TransferSlip'
                elif r['dtype'] == 2:
                    dtype = 'PO'
                else:
                    dtype = 'Invalid'

                apg.append((
                    r['pid'],
                    r['dst'] and 'HQ' or 'SF',
                    dtype,
                    sts,
                    r['doc_num'] or '',
                    d_users.get(r['uid'], 'UNK'),
                    r['pdesc'],
                    time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(r['ts']))
                ))
        
            cur.execute('select FOUND_ROWS()')
            
        else:
            cur.execute('select count(*) from inv_request t where '+ws)
            
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)


    def fn_delete_request(self):
        pid = self.req.psv_int('pid')

        cur = self.cur()
        cur.execute('delete from inv_request where pid=%s and (flg&1)=0', (pid,))
        self.req.writejs({'err': int(cur.rowcount<=0)})


    def fn_save_request(self):
        js = self.req.psv_js('js')

        cur = self.cur()

        pid = int(js['pid'])
        dtype = int(js['dtype'])
        dst = int(js['dst'])
        if dtype not in (1, 2): self.req.exitjs({'err': -1, 'pid':pid, 'errs': 'Invalid Type'})

        lst = [ map(int, f_x[:4]) for f_x in js['items'] if int(f_x[3]) > 0 ]

        desc = js['desc'].strip()
        if pid:
            cur.execute('select pjs from inv_request where pid=%s', (pid,))
            pjs = json.loads(cur.fetchall()[0][0])
            pjs['items'] = lst
            pjs = json.dumps(pjs, separators=(',',':'))

            cur.execute('update inv_request set rev=rev+1,dst=%s,pdesc=%s,pjs=%s where pid=%s and rev=%s and flg&1=0', (
                dst, desc, pjs, pid, js['rev']
                )
            )
        else:
            if not lst: self.req.exitjs({'err': -1, 'err_s': 'Empty Item List'})
            flg = 2
            pjs = {'items': lst}
            pjs = json.dumps(pjs, separators=(',',':'))
            cur.execute('insert into inv_request values(null,1,%s,%s,%s,0,0,%s,%s,%s,%s)', (
                dst, dtype, flg, int(time.time()), int(self.user_id), desc, pjs
                )
            )
            pid = cur.lastrowid

        self.req.writejs({'err':int(cur.rowcount<=0), 'pid':pid})


    def get_request(self, pid):
        cur = self.cur()
        cur.execute('select t.*,q.state,q.doc_num,q.js as qjs from inv_request t left join qbpos q on (t.qbpos_id=q.id) where pid=%s', (pid,))
        t = dict(zip(cur.column_names, cur.fetchall()[0]))
        js = json.loads(t['pjs'])['items']
        t['qjs'] = t['qjs'] and json.loads(t['qjs'])or {}
        t['pjs'] = js
        t['ts_s'] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(t['ts']))

        d_items = {}
        if js:
            cur.execute('select sid,num,name,detail from sync_items where sid in (%s)' % (','.join([str(int(f_x[0])) for f_x in js]),))
            for r in cur.fetchall():
                r = list(r)
                d_items[ r[0] ] = r
                r[0] = str(r[0])
                r[3] = json.loads(r[3])

        for r in js:
            j = d_items.get(r[0])
            r.append(j)
            r[0] = str(r[0])

        return t

    def fn_get_request(self):
        self.req.writejs( self.get_request(self.qsv_int('pid')) )

    def fn_print(self):
        ts = self.get_request(self.qsv_int('pid'))
        self.req.writefile('purchasing/ts_print.html', {'ts': ts})


    def fn_send(self):
        pid = self.req.psv_int('pid')

        cur = self.cur()
        cur.execute("select rev,dtype,qbpos_id,pjs from inv_request where pid=%s", (pid, ))
        rev,dtype,qbpos_id,pjs = cur.fetchall()[0]
        pjs = json.loads(pjs)['items']
        if not pjs: self.req.exitjs({'err': -1, 'err_s': 'Empty Item List'})

        if not qbpos_id:
            cur.execute("insert into qbpos values(null,1,2,-99,%s,%s,null,0,null)", (dtype,pid,))
            last_qbpos_id = cur.lastrowid
            cur.execute("update inv_request set rev=rev+1,qbpos_id=%s,flg=flg|1 where pid=%s and rev=%s and (flg&1)=0", (
                last_qbpos_id, pid, rev
                )
            )
            if cur.rowcount <= 0: self.req.exitjs({'err': -1, 'err_s': "can't send(1)"})
            qbpos_id = last_qbpos_id

        cur.execute("update qbpos set rev=rev+1,state=1,errno=0,js=null where id=%s and state=2 and errno!=0", (qbpos_id,))
        if cur.rowcount <= 0: self.req.exitjs({'err': -1, 'err_s': "can't send(2)"})

        self.req.writejs({'pid': pid})

    fn_send.PERM = PERM_ADMIN

