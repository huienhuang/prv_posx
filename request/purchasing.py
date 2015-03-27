import config
import hashlib
import bisect
import json
import time


DEFAULT_PERM = 1 << config.USER_PERM_BIT['purchasing']
class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        r = {
            'tab_cur_idx' : 2,
            'title': 'Purchasing',
            'tabs': [ ('item_margin', 'Item Margin'), ('item_markup', 'Item Markup'), ('price_adjustment', 'Price Adjustment') ]
        }
        self.req.writefile('tmpl_multitabs.html', r)
        
        
    def fn_cost_n_price_tool(self):
        self.req.writefile('purchasing/cost_n_price_tool.html')
    
    def fn_item_margin(self):
    	self.req.writefile('purchasing/item_margin.html')

    def fn_price_adjustment(self):
        self.req.writefile('purchasing/price_adjustment.html')

    
    def fn_get_dept_margin(self):
        js = self.get_data_file_cached('items_stat_v2', 'items_stat_v2.txt')
        if not js: return

        frm_dt = 0
        to_dt = 0xFFFFFFFF

        dt = self.qsv_str('frm')
        if dt:
            dt = map(int, dt.split('-'))
            frm_dt = dt[0] * 100 + dt[1]

        dt = self.qsv_str('to')
        if dt:
            dt = map(int, dt.split('-'))
            to_dt = dt[0] * 100 + dt[1]

        if frm_dt > to_dt: return

        d_cate_idx = {}
        cates = []
        k = 0
        for cnz,cd in js['cates'].items():
            l_cs = cd[0]
            mon_lst = [ f_v[0] for f_v in l_cs ]
            s = [0, 0, 0, 0]
            for i in range(bisect.bisect_left(mon_lst, frm_dt),  bisect.bisect_right(mon_lst, to_dt)):
                cs = l_cs[i][1]
                for j in range(len(cs)): s[j] += cs[j]
            if not s[3]: continue
            if s[1]:
                s = '%0.1f%%' % ((s[1] - s[2]) / s[1] * 100, )
            else:
                s = ''

            cates.append( (cnz, s, k) )
            d_cate_idx[cnz] = k
            k += 1

        cates.sort(key=lambda f_x: f_x[0])


        depts = []
        for dnz,dd in js['depts'].items():
            l_ds = dd[1]
            mon_lst = [ f_v[0] for f_v in l_ds ]
            s = [0, 0, 0, 0]
            for i in range(bisect.bisect_left(mon_lst, frm_dt),  bisect.bisect_right(mon_lst, to_dt)):
                ds = l_ds[i][1]
                for j in range(len(ds)): s[j] += ds[j]
            if not s[3]: continue
            if s[1]:
                s = '%0.1f%%' % ((s[1] - s[2]) / s[1] * 100, )
            else:
                s = ''

            depts.append( (dd[0][0] != None and str(dd[0][0]) or '', dd[0][1], d_cate_idx.get(dd[0][2]), s) )
        depts.sort(key=lambda f_x: (f_x[1] or '').lower())


        self.req.writejs({'cates': cates, 'depts': depts})



    def fn_get_margin_items(self):
        ret = {'res':{'len':0, 'apg':[]}}

        js = self.get_data_file_cached('items_stat_v2', 'items_stat_v2.txt')
        if not js: self.req.exitjs(ret)

        frm_dt = 0
        to_dt = 0xFFFFFFFF
        dt = self.qsv_str('frm')
        if dt:
            dt = map(int, dt.split('-'))
            frm_dt = dt[0] * 100 + dt[1]
        dt = self.qsv_str('to')
        if dt:
            dt = map(int, dt.split('-'))
            to_dt = dt[0] * 100 + dt[1]
        if frm_dt > to_dt: self.req.exitjs(ret)

        deptsid = self.qsv_int('sid', None)


        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)

        dept = js['depts'].get(deptsid)
        if not dept: self.req.exitjs(ret)

        items = js['items']
        dept_itemsids = dept[2]
        l_t = []
        for sid in dept_itemsids:
            u_dept,l_s = items[sid]
            mon_lst = [ f_v[0] for f_v in l_s ]
            s = [0, 0, 0, 0]
            for i in range(bisect.bisect_left(mon_lst, frm_dt),  bisect.bisect_right(mon_lst, to_dt)):
                es = l_s[i][1]
                for j in range(len(es)): s[j] += es[j]
            if not s[3]: continue
            l_t.append( (sid, s) )
        rlen = len(l_t)

        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            l_t = l_t[sidx * pgsz : sidx * pgsz + (eidx - sidx) * pgsz]
            if l_t:
                item_d = {}
                cur.execute('select sid,name,num from sync_receipts_items where sid in (%s)' % ( ','.join([str(f_x[0]) for f_x in l_t]) ))
                for r in cur.fetchall(): item_d[ r[0] ] = r

            for sid,s in l_t:
                sid,name,num = item_d.get(sid)

                if s[1]:
                    mg = '%0.1f%%' % ((s[1] - s[2]) / s[1] * 100, )
                else:
                    mg = ''

                r = (
                    num,
                    name,
                    s[1] and '%0.2f' % (s[1], ) or '',
                    mg,
                    str(sid)
                )
                apg.append(r)

        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)



    def fn_item_markup(self):
        self.req.writefile('purchasing/item_markup.html')


    def fn_get_item_markup(self):
        ret = {'res':{'len':0, 'apg':[]}}

        js = self.get_data_file_cached('items_markup', 'items_markup.txt')
        if not js: self.req.exitjs(ret)

        mu_t = self.req.qsv_int('mu_t')
        mu_v = self.req.qsv_int('mu_v')

        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)

        l_t = []
        for t in js:
            if mu_t:
                p = t[2][mu_t - 1]
                if p != None and p <= mu_v: l_t.append( (t[0], p) )

            else:
                pl = t[2]
                for i in range(5):
                    p = pl[i]
                    if p != None and p <= mu_v:
                        l_t.append( (t[0], p) )
                        break
        rlen = len(l_t)

        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            l_t = l_t[sidx * pgsz : sidx * pgsz + (eidx - sidx) * pgsz]
            if l_t:
                item_d = {}
                cur.execute('select sid,name,num from sync_items where sid in (%s)' % ( ','.join([str(f_x[0]) for f_x in l_t]) ))
                for r in cur.fetchall(): item_d[ r[0] ] = r

            for sid,s in l_t:
                sid,name,num = item_d.get(sid)

                r = (
                    num,
                    name,
                    '%d%%' % (s, ),
                    str(sid)
                )
                apg.append(r)

        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)


    def fn_load_history(self):
        sid = self.qsv_str('sid')
        
        ws = ''
        if sid: ws = ' and t.ref=%d' % (int(sid), )

        cur= self.cur()
        cur.execute("select t.*,q.state,q.errno,q.js,p.ponum,p.global_js from inv_request t left join sync_purchaseorders p on (t.ref=p.sid) left join qbpos q on (t.qbpos_id=q.id) where t.dtype=3 "+ws+" order by t.pid desc limit 10")
        cnz = cur.column_names
        lst = []
        for r in cur.fetchall():
            r = dict(zip(cnz, r))

            r['pjs'] = r['pjs'] and json.loads(r['pjs']) or {}
            r['js'] = r['js'] and json.loads(r['js']) or {}
            r['gjs'] = r['global_js'] and json.loads(r['global_js']) or {}
            r['ref'] = str(r['ref'])
            del r['global_js']

            sts = 'Pending'
            if r['flg'] & 1:
                sts = 'Transfering'
                if r['state'] == 2:
                    if not r['errno']:
                        sts = 'Transfered'
                    else:
                        sts = 'Error'
            r['sts'] = sts

            lst.append(r)

        self.req.writejs(lst)

    def fn_load_po(self):
        po_id = self.qsv_str('po_id')

        cur = self.cur()
        cur.execute("select * from sync_purchaseorders where ponum=%s", (po_id,))
        rows = cur.fetchall()
        if not rows: return
        r = dict(zip(cur.column_names, rows[0]))

        ijs = r['ijs'] =  json.loads(r['items_js'])
        r['gjs'] =  json.loads(r['global_js'])
        r['items_js'] = r['global_js'] =  None
        r['sid'] = str(r['sid'])

        sids = [ str(f_x['itemsid']) for f_x in ijs ]
        if sids:
            items = {}
            cur.execute("select sid,detail,detail2 from sync_items where sid in (%s)" % (','.join(sids),))
            for rr in cur.fetchall(): items[ rr[0] ] = rr

            for rr in ijs:
                item = items[ rr['itemsid'] ]
                rr['itemsid'] = str(rr['itemsid'])
                js = rr['js'] = json.loads(item[1])
                #js['units'] = dict([(f_x[2].lower(), f_x) for f_x in js['units']])
                rr['js2'] = json.loads(item[2])

        self.req.writejs(r)


    def fn_adjust_po(self):
        po = self.req.psv_js('js')
        
        for r in po['ijs']:
            r['units'] = [ list(map(lambda f_x: round(f_x, 2), f_u[:-2])) + [f_u[-2], int(f_u[-1])] for f_u in r['units'] ]
            r['cost'] = round(r['cost'], 2)
            r['new_cost'] = round(r['new_cost'], 2)
            r['new_diff'] = round(r['new_diff'], 2)
            r['sid'] = int(r['sid'])

        js = {
            'ijs': po['ijs'],
        }
        
        cur = self.cur()
        js_s = json.dumps(js, separators=(',',':'))
        cur.execute('insert into inv_request values (null,1,0,3,1,%s,0,%s,%s,%s,%s)', (
            int(po['sid']), int(time.time()), self.user_id, '', js_s
            )
        )
        pid = cur.lastrowid
        cur.execute("insert into qbpos values(null,1,0,-99,3,%s,null,0,null)", (pid,))
        qbpos_id = cur.lastrowid
        cur.execute("update inv_request set rev=rev+1,qbpos_id=%s where pid=%s", (qbpos_id, pid))
        cur.execute("update qbpos set rev=rev+1,state=1 where id=%s", (qbpos_id,))

        self.req.writejs( {'pid': pid} )


    def fn_get_po_sid_by_num(self):
        num = self.req.qsv_int('num')

        cur = self.cur()
        cur.execute("select sid from sync_purchaseorders where ponum=%s order by sid asc", (num, ))
        rows = cur.fetchall()
        sid = rows and str(rows[0][0]) or ''

        self.req.writejs({'sid': sid})



