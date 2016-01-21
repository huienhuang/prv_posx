import config
import hashlib
import bisect
import time
import json
import urllib

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
        #{'id': 'pohelper', 'name': 'PO Helper', 'src': 'pohelper'},
        {'id': 'itemsold', 'name': 'Item Sold', 'src': 'itemsold'},

        {'id': 'store_po_home', 'name': 'PO List', 'src': '?fn=store_po_home'},
        {'id': 'store_po', 'name': 'PO View', 'src': '?fn=store_po'},

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
        dst = 1#int(js['dst'])
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



    def fn_store_po(self):
        self.req.writefile('purchasing/store_po.html', {'stores': config.stores, 'store_name': config.store_name})



    def fn_get_items_lite(self):
        nums = self.req.qsv_ustr('nums').split('|')
        nums_s = ','.join(set([ str(int(f_x)) for f_x in nums ]))

        rs = {}
        cur = self.cur()
        cur.execute('select sid,num,name,detail,detail2 from sync_items where num in (%s)' % (nums_s, ))
        for r in cur.fetchall():
            jsa = json.loads(r[3])
            jsb = json.loads(r[4])

            rs[ r[1] ] = {
                'sid': str(r[0]),
                'name': r[2],
                #'order_uom_idx': jsa['order_uom_idx'],
                'units': [ f_x[1:] for f_x in jsa['units'] ],
                'last_cost': jsb['costs'][0]
            }

        self.req.writejs(rs)


    #def fn_test(self):
    #    self.req.writejs( self.intcom('LOCAL', '/ts_request?fn=get_items_lite&nums=13100') )

    def get_remote_items(self, snz, nums):
        d = urllib.urlencode({'fn': 'get_items_lite', 'nums': '|'.join(map(str, nums))})
        return json.loads(self.intcom(snz, '/ts_request?' + d))


    def fn_get_remote_items(self):
        snz = self.req.qsv_ustr('snz')
        nums = set(map(int, self.req.qsv_ustr('nums').split('|')))

        self.req.writejs({'err': 0, 'ret': self.get_remote_items(snz, nums)})


    def fn_get_items_mapping(self):
        snz = self.req.qsv_ustr('snz')
        nums = set(map(int, self.req.qsv_ustr('nums').split('|')))

        cur = self.cur()
        cur.execute('select local_num,remote_num from item_mapping where local_num in (%s) and store_nz=%%s' % (','.join(map(str, nums)), ), (snz, ))
        rs = dict(cur.fetchall())

        self.req.writejs({'err': 0, 'ret' : rs})


    def fn_api_insert_so(self):
        js = self.req.psv_js('js')
        lst = [ {'sid': v['sid'], 'uom': v['uom'], 'qty': v['qty'], 'price': v['price']} for v in js['lst'] ]

        req_js = json.dumps({'lst': lst, 'ref_id': int(js['ref_id']), 'sid_customer': int(js['sid_customer'])}, separators=(',',':'))
        cur = self.cur()
        cur.execute('insert into api_req values(null,0,1,0,%s,%s,null,%s,%s)', (
            'new_so', req_js, int(time.time()), 0
        ))
        rid= cur.lastrowid

        self.req.writejs({'rid': rid})

    def remote_api_insert_so(self, snz, js):
        d = urllib.urlencode({'js': json.dumps(js, separators=(',',':'))})
        return json.loads(self.intcom(snz, '/ts_request?fn=api_insert_so', d))


    def fn_save_store_po(self):
        js = self.req.psv_js('js')
        if not js['lst']: return

        po_config = self.get_config_js("store_po_config", {})
        sid_vendor = int(po_config.get('sid_vendor'))
        sid_customer = int(po_config.get('sid_customer'))


        snz = js['snz']

        po_lst = []
        so_lst = []
        lst = []
        mapping = []
        for sid, num, uom, qty, r_sid, rnum, price in js['lst']:
            price = float(price)
            qty = int(qty)
            uom = uom or ''
            sid = int(sid)
            r_sid = int(r_sid)
            rnum = int(rnum)
            num = int(num)

            lst.append( {'sid': sid, 'uom': uom, 'qty': qty, 'price': price, 'r_sid': r_sid, 'rnum': rnum, 'num': num} )
            po_lst.append( {'sid': sid, 'uom': uom, 'qty': qty, 'price': price} )
            so_lst.append( {'sid': r_sid, 'uom': uom, 'qty': qty, 'price': price} )
            if num != rnum: mapping.append( [num, rnum, snz] )

        
        cur = self.cur()
        cur.execute('insert into store_po values (null,%s,0,0,%s,%s,0,null,%s)', (
            self.user_id, snz, json.dumps({'lst': lst}, separators=(',',':')),
            int(time.time())
        ))
        store_po_id= cur.lastrowid

        if mapping: cur.executemany('replace into item_mapping values(%s,%s,%s)', mapping)

        r_rid = self.remote_api_insert_so(snz, {'lst': so_lst, 'ref_id': store_po_id, 'sid_customer': sid_customer})['rid']

        req_js = json.dumps({'lst': po_lst, 'ref_id': store_po_id, 'sid_vendor': sid_vendor}, separators=(',',':'))
        cur.execute('insert into api_req values(null,0,1,0,%s,%s,null,%s,%s)', (
            'new_po', req_js, int(time.time()), 0
        ))
        rid= cur.lastrowid

        cur.execute('update store_po set api_req_id=%s,r_api_req_id=%s where id=%s', (
            rid, r_rid, store_po_id
        ))

        self.req.writejs({'id': store_po_id})



    def fn_load_store_po(self):
        sp_id = self.req.qsv_int('id')
        cur = self.cur()

        cur.execute("select * from store_po where id=%s", (sp_id, ))
        rows = cur.fetchall()
        r = dict(zip(cur.column_names, rows[0]))

        r['js'] = json.loads(r['js'])
        if r['remote_api_res_js']: r['remote_api_res_js'] = json.loads(r['remote_api_res_js'])


        cur.execute('select sid,num,name,detail from sync_items where sid in (%s)' % (
            ','.join(str(f_x['sid']) for f_x in r['js']['lst'])
        ))
        items = dict((f_x[0], f_x) for f_x in cur.fetchall())

        lst = []
        for t in r['js']['lst']:
            td = items.get(t['sid'], [None, t['num'], 'Not Found', None])
            t_js = td[3] and json.loads(td[3]) or {'units': []}

            k = -1
            for i in range(len(t_js['units'])):
                u = t_js['units'][i]
                if t['uom'].lower() == u[2].lower():
                    k = i
                    break

            if k == -1:
                k = len(t_js['units'])
                t_js['units'].append(None, '', t['uom'], 1, '')

            t_js['default_uom_idx'] = k
            t_js['rnum'] = t['rnum']
            t_js['qty'] = t['qty']

            lst.append([ str(t['sid']), t['num'], td[2], t_js ])

        r['js'] = lst

        self.req.writejs(r)


    def fn_store_po_home(self):
        self.req.writefile("purchasing/store_po_list.html", {})

    def fn_get_store_po_list(self):
        ret = {'res':{'len':0, 'apg':[]}}

        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)

        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            d_users = dict([f_v[:2] for f_v in self.getuserlist()])
            cur.execute('select SQL_CALC_FOUND_ROWS p.*,a.res_js from store_po p left join api_req a on (p.api_req_id=a.id) order by p.id desc limit %d,%d' % (
                        sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            nzs = cur.column_names
            for r in cur:
                r = dict(zip(nzs, r))

                r['res_js'] = r['res_js'] and json.loads(r['res_js']) or {}
                r['remote_api_res_js'] = r['remote_api_res_js'] and json.loads(r['remote_api_res_js']) or {}

                apg.append((
                    r['id'],
                    r['store_nz'],
                    r['remote_api_res_js'].get('res_js', {}).get('num') or '',
                    r['res_js'].get('num') or '',
                    d_users.get(r['user_id']) or 'UNK(%d)' % (r['user_id'],),

                    time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(r['cts']))
                ))
        
            cur.execute('select FOUND_ROWS()')
            
        else:
            cur.execute('select count(*) from store_po')
            
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)


    def fn_get_api_res(self):
        rids = [str(int(f_x)) for f_x in self.req.qsv_ustr('rids').split('|')]

        cur = self.cur()
        cur.execute('select id,state,ret,res_js,cts,lts from api_req where id in (%s) and state=2' % ( ','.join(rids), ))
        nzs = cur.column_names
        rows = []
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            r['res_js'] = json.loads(r['res_js'])
            rows.append(r)

        self.req.writejs(rows)


    def fetch_remote_api_res(self, snz, rids):
        d = urllib.urlencode({'fn': 'get_api_res', 'rids': '|'.join(map(str, rids))})
        return json.loads(self.intcom(snz, '/ts_request?' + d))

    def fn_fetch_remote_api_res(self):
        cur = self.cur()
        cur.execute('select r_api_req_id,id,store_nz from store_po where remote_api_res_upd=0 and r_api_req_id!=0')
        grs = {}
        for r in cur.fetchall():
            grs.setdefault(r[2], {})[ r[0] ] = r[1]

        for store_nz, reqs in grs.items():
            for r in self.fetch_remote_api_res(store_nz, reqs.keys()):
                sp_id = reqs[ r['id'] ]
                remote_api_res_js = json.dumps(r, separators=(',',':'))
                cur.execute('update store_po set remote_api_res_upd=1,remote_api_res_js=%s where id=%s', (
                    remote_api_res_js,
                    sp_id
                ))

        self.req.writejs({'err': 0})

    def fn_get_store_po_config(self):
        self.req.writejs( self.get_config_js("store_po_config", {}) )

    def fn_set_store_po_config(self):
        r = {
            'sid_vendor': str(self.req.psv_int('sid_vendor')),
            'sid_customer': str(self.req.psv_int('sid_customer'))
        }
        self.set_config_js("store_po_config", r)

        self.req.writejs({'err': 0})

