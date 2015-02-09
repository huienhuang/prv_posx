import config
import hashlib
import bisect
import time
import json

DEFAULT_PERM = 1 << config.USER_PERM_BIT['purchasing_mgr']
class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        tabs = [{'id': 'PO', 'name': 'PO'}, {'id': 'View', 'name': 'View', 'src': '?fn=View'}]
        r = {
            'tab_cur_idx' : 2,
            'title': 'PO REQUEST',
            'tabs': tabs
        }
        self.req.writefile('tmpl_multitabs_v2.html', r)


    def fn_po(self):
        self.req.writefile('purchasing/po_list.html')
        
    def fn_view(self):
        self.req.writefile('purchasing/po_request.html')
        
    
    def fn_get_lst(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        ws = ''
        flg = self.qsv_int('flg')
        if flg == 1:
            ws = ' where flg&1=0'
        elif flg == 2:
            ws = ' where flg&1=1'

        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)

        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            d_users = dict([f_v[:2] for f_v in self.getuserlist()])
            cur.execute('select SQL_CALC_FOUND_ROWS * from po%s order by pid desc limit %d,%d' % (
                        ws, sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            nzs = cur.column_names
            for r in cur:
                r = dict(zip(nzs, r))

                apg.append((
                    r['pid'],
                    (r['flg'] & 1) and 'Transfered' or 'Pending',
                    r['pno'] or '',
                    d_users.get(r['uid'], 'UNK'),
                    r['pdesc'],
                    time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(r['ts']))
                ))
        
            cur.execute('select FOUND_ROWS()')
            
        else:
            cur.execute('select count(*) from po'+ws)
            
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)


    def fn_delete_po(self):
        pid = self.req.psv_int('pid')

        cur = self.cur()
        cur.execute('delete from po where pid=%s', (pid,))
        self.req.writejs({'err': int(cur.rowcount<=0)})
    
    def fn_save_po(self):
        js = self.req.psv_js('js')

        cur = self.cur()

        pid = int(js['pid'])
        lst = [ map(int, f_x[:4]) for f_x in js['items'] if int(f_x[3]) > 0 ]

        js_lst = json.dumps(lst, separators=(',',':'))
        desc = js['desc'].strip()

        rev = 0
        if pid:
            cur.execute('update po set rev=rev+1,pdesc=%s,pjs=%s where pid=%s and rev=%s and flg&2=0', (
                desc, js_lst, pid, js['rev']
                )
            )
        else:
            cur.execute('insert into po values(null,1,0,0,0,%s,%s,%s,%s)', (
                int(time.time()), int(self.user_id), desc, js_lst
                )
            )
            pid = cur.lastrowid

        self.req.writejs({'err':int(cur.rowcount<=0), 'pid':pid})

    def fn_get_po(self):
        pid = self.qsv_int('pid')

        cur = self.cur()
        cur.execute('select * from po where pid=%s', (pid,))
        t = dict(zip(cur.column_names, cur.fetchall()[0]))
        js = json.loads(t['pjs'])
        t['pjs'] = js

        d_items = {}
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

        self.req.writejs(t)

