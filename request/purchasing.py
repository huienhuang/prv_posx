import config
import hashlib
import bisect

DEFAULT_PERM = 1 << config.USER_PERM_BIT['purchasing_mgr']
class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        r = {
            'tab_cur_idx' : 2,
            'title': 'Purchasing',
            'tabs': [ ('item_margin', 'Item Margin'), ]

        }
        self.req.writefile('tmpl_multitabs.html', r)
        
        
    def fn_cost_n_price_tool(self):
        self.req.writefile('purchasing/cost_n_price_tool.html')
    
    def fn_item_margin(self):
    	self.req.writefile('purchasing/item_margin.html')

    
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


