import config
import hashlib
import bisect
import json
import time
import const
import cPickle
import cStringIO
import csv
import urllib


CFG = {
    'id': 'purchasing_C0000000',
    'name': 'Purchasing',
    'perm_list': [
    ('access', ''),
    ]
}


PERM_ADMIN = 1 << 1

class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        r = {
            'tab_cur_idx' : 2,
            'title': 'Purchasing',
            'tabs': [
            ('item_margin', 'Item Margin'),
            ('item_markup', 'Item Markup'),
            ('price_adjustment', 'Price Adjustment'),
            ('$itemsold', 'Item Sold'),
            ('out_of_stock', 'Out Of Stock'),
            ('over_stock', 'Over Stock'),
            ]
        }
        self.req.writefile('tmpl_multitabs.html', r)
        
        
    def fn_cost_n_price_tool(self):
        self.req.writefile('purchasing/cost_n_price_tool.html')
    
    def fn_item_margin(self):
    	self.req.writefile('purchasing/item_margin.html')

    def fn_price_adjustment(self):
        self.req.writefile('purchasing/price_adjustment.html')

    def fn_out_of_stock(self):
        r = {'const':const}
        self.req.writefile('purchasing/out_of_stock.html', r)

    def fn_over_stock(self):
        r = {'const':const}
        self.req.writefile('purchasing/over_stock.html', r)
    
    def get_items(self, frm_mon, to_mon, status_l, dept_l, sidx, eidx, pgsz, mode=0):
        where = []
        if not status_l or not dept_l: return (0, [])
        
        s_status = set([ str(int(f_x)) for f_x in status_l.split('|') ])
        where.append('status in (%s)' % (','.join(s_status),))
        
        l_depts = cPickle.loads(self.getconfigv2('departments'))
        d_depts = dict(l_depts)
        s_dept = set()
        for dept in dept_l.split('|'):
            deptsid = d_depts.get(dept.strip().lower())
            if deptsid == None: continue
            s_dept.add(deptsid)
            
        if not s_dept: return (0, [])
        where.append('deptsid in (%s)' % (','.join(map(str, s_dept))))
        
        if where:
            where = ' where ' + ' AND '.join(where)
        else:
            where = ''
        
        cur = self.cur()
        apg = []
        if mode or pgsz > 0 and sidx >= 0 and sidx < eidx:
            d_r_depts = dict([(f_b, f_a) for f_a,f_b in l_depts])
            d_r_status = dict([(f_b, f_a) for f_a,f_b in const.ITEM_L_STATUS])
            
            #items = self.get_items_stat()
            cur.execute('select SQL_CALC_FOUND_ROWS sid,num,name,status,deptsid,detail from sync_items'+where+' order by num asc,sid asc'
                        + (not mode and ' limit %d,%d' % (sidx * pgsz, (eidx - sidx) * pgsz) or '')
            )
            nzs = cur.column_names
            for r in cur:
                r = dict(zip(nzs, r))
                r['jsd'] = jsd = json.loads(r['detail'])
                unit = jsd['units'][ jsd['default_uom_idx'] ]
                if not unit[3]: unit = jsd['units'][0]
                
                l_qty = jsd['qty']
                s_qty = 0
                s_price = 0
                s_cost = 0
                """
                if frm_mon <= to_mon and to_mon:
                    stat = items.get(r['sid'], (None, None, []))[2]
                    mon_lst = [ f_x[0] for f_x in stat ]
                    for i in range( bisect.bisect_left(mon_lst, frm_mon),  bisect.bisect_right(mon_lst, to_mon) ):
                        s = stat[i]
                        s_qty += s[1]
                        s_price += s[2]
                        s_cost += s[3]
                """
                if unit[3] != 1:
                    s_qty /= unit[3]
                    l_qty = map(lambda f_x: f_x / unit[3], l_qty)
                
                dept = d_r_depts.get(r['deptsid'])
                cate = const.ITEM_D_DEPT.get(dept)
                
                r['s_status'] = d_r_status.get(r['status'])
                r['s_dept'] = dept
                r['s_cate'] = cate
                r['unit'] = unit
                r['l_qty'] = l_qty
                r['l_stat'] = [s_qty, s_price, s_cost]
                
                apg.append(r)
                
            cur.execute('select FOUND_ROWS()')
            
        else:
            cur.execute('select count(*) from sync_items'+where)
            
        rlen = int(cur.fetchall()[0][0])
    
        return (rlen, apg)
    
    def fn_get_items(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        pgsz = self.req.psv_int('pagesize')
        sidx = self.req.psv_int('sidx')
        eidx = self.req.psv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        frm_mon = self.req.psv_int('frm_mon')
        to_mon = self.req.psv_int('to_mon')
        status_l = self.req.psv_str('status')
        dept_l = self.req.psv_str('dept')
        
        rlen, apg_ = self.get_items(frm_mon, to_mon, status_l, dept_l, sidx, eidx, pgsz)
        apg = []
        for r in apg_:
            l_stat = r['l_stat']
            s_mgn = l_stat[1] - l_stat[2]
            apg.append(
                [
                    r['num'],
                    r['unit'][1],
                    r['name'],
                    r['unit'][2],
                    r['s_status'] or '',
                    r['s_cate'] or '',
                    r['s_dept'] or '',
                    r['l_qty'][0] and int(r['l_qty'][0]) or '',
                    r['l_qty'][3] and int(r['l_qty'][3]) or '',
                    l_stat[0] and int(l_stat[0]) or '',
                    l_stat[1] and '%0.2f' % (l_stat[1],) or '',
                    l_stat[2] and '%0.2f' % (l_stat[2],) or '',
                    s_mgn and '%0.2f' % (s_mgn,) or '',
                    l_stat[1] and '%0.2f%%' % (s_mgn * 100 / l_stat[1],) or '',
                    str(r['sid'])
                    ]
            )
        
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
    

    def fn_export_csv(self):
        js = self.req.psv_js('js')
        frm_mon = js['frm_mon'].isdigit() and int(js['frm_mon']) or 0
        to_mon = js['to_mon'].isdigit() and int(js['to_mon']) or 0
        status_l = js['status'].strip()
        dept_l = js['dept'].strip()
        
        rlen, apg_ = self.get_items(frm_mon, to_mon, status_l, dept_l, 0, 0, 0, 1)
        apg = []
        for r in apg_:
            l_stat = r['l_stat']
            s_mgn = l_stat[1] - l_stat[2]
            apg.append(
                [
                    r['num'],
                    r['unit'][1],
                    r['name'],
                    r['unit'][2],
                    r['s_status'] or '',
                    r['s_cate'] or '',
                    r['s_dept'] or '',
                    r['l_qty'][0] and int(r['l_qty'][0]) or '',
                    r['l_qty'][3] and int(r['l_qty'][3]) or '',
                    l_stat[0] and int(l_stat[0]) or '',
                    l_stat[1] and '%0.2f' % (l_stat[1],) or '',
                    l_stat[2] and '%0.2f' % (l_stat[2],) or '',
                    s_mgn and '%0.2f' % (s_mgn,) or '',
                    l_stat[1] and '%0.2f%%' % (s_mgn * 100 / l_stat[1],) or '',
                    str(r['sid'])
                    ]
            )
        
        fp = cStringIO.StringIO()
        wt = csv.writer(fp)
        wt.writerow(['#ID', 'ALU', 'Name', 'UOM', 'Status', 'Cate', 'Dept', 'OnHand', 'OnOrder'])
        for r in apg: wt.writerow(map(lambda f_x: unicode(f_x).encode('utf8'), r[:-6]))
        
        self.req.out_headers['content-type'] = 'application/octet-stream'
        self.req.out_headers['content-disposition'] = 'attachment; filename="data.csv"'
        self.req.write( fp.getvalue() )



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
        cur.execute("select * from sync_purchaseorders where ponum=%s and (status>>16)=0 order by sid desc", (po_id,))
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
        num = self.req.qsv_ustr('num')
        if not num.isdigit(): self.req.exitjs({'sid': ''})

        cur = self.cur()
        cur.execute("select sid from sync_purchaseorders where ponum=%s and (status>>16)=0 order by sid asc", (int(num), ))
        rows = cur.fetchall()
        sid = rows and str(rows[0][0]) or ''

        self.req.writejs({'sid': sid})



    def get_items_x(self, mon_B, qty_M, status_l, dept_l, sidx, eidx, pgsz, mode=0):
        where = []
        if not status_l or not dept_l or not qty_M: return (0, [])
        
        s_status = set([ int(f_x) for f_x in status_l.split('|') if f_x ])
        
        l_depts = cPickle.loads(self.getconfigv2('departments'))
        d_depts = dict(l_depts)
        s_dept = set()
        for dept in dept_l.split('|'):
            if not dept: continue
            deptsid = d_depts.get(dept.strip().lower())
            if deptsid == None: continue
            s_dept.add(deptsid)
        
        mon_B = set([ int(f_x) for f_x in mon_B.split('|') if f_x ])

        if not s_dept or not mon_B: return (0, [])


        nts = []
        items = self.get_items_stat_x2()
        for k,v in items.items():
            if v[4] not in s_status: continue
            if v[3] not in s_dept: continue

            avg_qty = round(sum([ v[0][f_i] for f_i in range(len(v[0])) if (6 - f_i) in mon_B ]) / len(mon_B), 2)
            if v[1][2] + v[1][3] < avg_qty * qty_M: continue

            nts.append( (k, v, avg_qty) )
        nts.sort(key=lambda f_v: (v[1][2], v[0]))
        
        
        apg = []
        if mode or pgsz > 0 and sidx >= 0 and sidx < eidx:
            its = nts[ sidx * pgsz : sidx * pgsz + (eidx - sidx) * pgsz ]
            if its:
                d_r_depts = dict([(f_b, f_a) for f_a,f_b in l_depts])
                d_r_status = dict([(f_b, f_a) for f_a,f_b in const.ITEM_L_STATUS])

                ids = ','.join([ str(f_v[0]) for f_v in its ])
                cur = self.cur()
                cur.execute('select sid,num,name,status,deptsid,detail from sync_items where sid in (%s) order by num asc,sid asc' % (
                    ids,
                ))
                tlus = {}
                nzs = cur.column_names
                for r in cur:
                    r = dict(zip(nzs, r))
                    tlus[ r['sid'] ] = r

                    r['jsd'] = jsd = json.loads(r['detail'])

                    dept = d_r_depts.get(r['deptsid'])
                    cate = const.ITEM_D_DEPT.get(dept)
                    
                    r['s_status'] = d_r_status.get(r['status'])
                    r['s_dept'] = dept
                    r['s_cate'] = cate
                    

                for t in its:
                    r = tlus.get(t[0])
                    if not r:
                        r = {
                        'sid': t[0],
                        'num': t[1][2],
                        'unit': ['', '', ''],
                        'name': '',
                        's_status': '',
                        's_cate': '',
                        's_dept': '',
                        'l_qty': [0, 0, 0, 0, 0],
                        'l_stat': [0, 0, 0],
                        }

                    else:
                        jsd = r['jsd']
                        unit = jsd['units'][ jsd['default_uom_idx'] ]
                        if not unit[3]: unit = jsd['units'][0]

                        l_qty = jsd['qty'] + [t[2]]
                        if unit[3] != 1:
                            l_qty = map(lambda f_x: f_x / unit[3], l_qty)

                        r['unit'] = unit
                        r['l_qty'] = l_qty

                    apg.append(r)

        
        rlen = len(nts)
        return (rlen, apg)
    


    def fn_get_items_x(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        pgsz = self.req.psv_int('pagesize')
        sidx = self.req.psv_int('sidx')
        eidx = self.req.psv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        mon_l = self.req.psv_str('mon_l')
        mul = self.req.psv_int('mul')
        status_l = self.req.psv_str('status')
        dept_l = self.req.psv_str('dept')
        
        rlen, apg_ = self.get_items_x(mon_l, mul, status_l, dept_l, sidx, eidx, pgsz)
        apg = []
        for r in apg_:
            apg.append(
                [
                    r['num'],
                    r['unit'][1],
                    r['name'],
                    r['unit'][2],
                    r['s_status'] or '',
                    r['s_cate'] or '',
                    r['s_dept'] or '',
                    r['l_qty'][0] and int(r['l_qty'][0]) or '',
                    r['l_qty'][1] and int(r['l_qty'][1]) or '',
                    r['l_qty'][3] and int(r['l_qty'][3]) or '',
                    r['l_qty'][4] and "%0.1f" % r['l_qty'][4] or '',
                    str(r['sid'])
                    ]
            )
        
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
    

    def fn_store_po(self):
        self.req.writefile('store_po.html', {'stores': config.stores, 'store_name': config.store_name})



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


    def fn_test(self):
        self.req.writejs( self.intcom('LOCAL', '/purchasing?fn=get_items_lite&nums=13100') )

    def get_remote_items(self, snz, nums):
        d = urllib.urlencode({'fn': 'get_items_lite', 'nums': '|'.join(map(str, nums))})
        return json.loads(self.intcom(snz, '/purchasing?' + d))


    def get_items_mapping(self, snz, nums):
        cur = self.cur()
        cur.execute('select local_num,remote_num from item_mapping where local_num in (%s) and store_nz=%%s' % (','.join(map(str, nums)), ), (snz, ))
        rs = dict(cur.fetchall())
        s = set()
        for num in nums:
            if not rs.get(num):
                s.add(num)
                rs[num] = None
            else:
                s.add(rs[num])

        items = self.get_remote_items(snz, s)

        return {'mapping': rs, 'items': items}


    def fn_get_items_mapping(self):
        snz = self.req.qsv_ustr('snz')
        nums = set(map(int, self.req.qsv_ustr('nums').split('|')))

        self.req.writejs(self.get_items_mapping(snz, nums))







