import config
import hashlib
import bisect
import time
import json




class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        tabs = [{'id': 'PO', 'name': 'PO'}, {'id': 'View', 'name': 'View', 'src': '?fn=View'}]
        r = {
            'tab_cur_idx' : 2,
            'title': 'PO Request',
            'tabs': tabs
        }
        self.req.writefile('tmpl_multitabs_v2.html', r)


    def fn_transfer(self):
        self.req.writefile('purchasing/po_list.html')
        
    def fn_view(self):
        self.req.writefile('purchasing/po_request.html')
        
    
    def fn_get_lst(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        ws = ''
        flg = self.qsv_int('flg')
        if flg == 1:
            ws = ' where t.flg&1=0'
        elif flg == 2:
            ws = ' where t.flg&1=1'

        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)

        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            d_users = dict([f_v[:2] for f_v in self.getuserlist()])
            cur.execute('select SQL_CALC_FOUND_ROWS t.*,q.state,q.doc_num from transferslip t left join qbpos q on (t.qbpos_id=q.id) %s order by pid desc limit %d,%d' % (
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
                        sts = 'Transfered'
                    elif r['state'] < 0:
                        sts = 'Error'

                apg.append((
                    r['pid'],
                    sts,
                    r['doc_num'] or '',
                    d_users.get(r['uid'], 'UNK'),
                    r['pdesc'],
                    time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(r['ts']))
                ))
        
            cur.execute('select FOUND_ROWS()')
            
        else:
            cur.execute('select count(*) from transferslip'+ws)
            
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)


    def fn_delete_transfer_slip(self):
        pid = self.req.psv_int('pid')

        cur = self.cur()
        cur.execute('delete from transferslip where pid=%s and qbpos_id=0', (pid,))
        self.req.writejs({'err': int(cur.rowcount<=0)})


    def fn_save_transfer_slip(self):
        js = self.req.psv_js('js')

        cur = self.cur()

        pid = int(js['pid'])
        lst = [ map(int, f_x[:4]) for f_x in js['items'] if int(f_x[3]) > 0 ]

        js_lst = json.dumps(lst, separators=(',',':'))
        desc = js['desc'].strip()

        rev = 0
        if pid:
            cur.execute('update transferslip set rev=rev+1,pdesc=%s,pjs=%s where pid=%s and rev=%s and flg&1=0', (
                desc, js_lst, pid, js['rev']
                )
            )
        else:
            if not lst: self.req.exitjs({'err': -1, 'err_s': 'Empty Item List'})
            cur.execute('insert into transferslip values(null,1,0,0,0,%s,%s,%s,%s)', (
                int(time.time()), int(self.user_id), desc, js_lst
                )
            )
            pid = cur.lastrowid

        self.req.writejs({'err':int(cur.rowcount<=0), 'pid':pid})


    def get_transfer_slip(self, pid):
        cur = self.cur()
        cur.execute('select t.*,q.state,q.doc_num,q.js as qjs from transferslip t left join qbpos q on (t.qbpos_id=q.id) where pid=%s', (pid,))
        t = dict(zip(cur.column_names, cur.fetchall()[0]))
        js = json.loads(t['pjs'])
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

    def fn_get_transfer_slip(self):
        self.req.writejs( self.get_transfer_slip(self.qsv_int('pid')) )

    def fn_print(self):
        ts = self.get_transfer_slip(self.qsv_int('pid'))
        self.req.writefile('purchasing/ts_print.html', {'ts': ts})


    def fn_send(self):
        pid = self.req.psv_int('pid')

        cur = self.cur()
        cur.execute("select rev,qbpos_id,pjs from transferslip where pid=%s", (pid, ))
        rev,qbpos_id,pjs = cur.fetchall()[0]
        pjs = json.loads(pjs)
        if not pjs: self.req.exitjs({'err': -1, 'err_s': 'Empty Item List'})

        if not qbpos_id:
            cur.execute("insert into qbpos values(null,1,0,0,1,%s,null,0,null)", (pid,))
            last_qbpos_id = cur.lastrowid
            cur.execute("update transferslip set rev=rev+1,qbpos_id=%s,flg=flg|1 where pid=%s and rev=%s and (flg&1)=0", (
                last_qbpos_id, pid, rev
                )
            )
            if cur.rowcount <= 0: self.req.exitjs({'err': -1, 'err_s': "can't send(1)"})
            qbpos_id = last_qbpos_id

        cur.execute("update qbpos set rev=rev+1,state=1,errno=0,js=null where id=%s and state<=0", (qbpos_id,))
        if cur.rowcount <= 0: self.req.exitjs({'err': -1, 'err_s': "can't send(2)"})

        self.req.writejs({'pid': pid})

    fn_send.PERM = 1 << config.USER_PERM_BIT['purchasing_mgr']

    