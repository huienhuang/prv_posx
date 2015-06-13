import config
import hashlib
import json
import cPickle
import bisect
import const
import csv
import cStringIO



CFG = {
    'id': 'ItemReport_BF100000',
    'name': 'Item Report',
    'perm_list': [
    ('access', ''),
    ]
}


class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        r = {'const':const}
        self.req.writefile('report_item_sale.html', r)
        
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
            
            items = self.get_items_stat()
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
                
                if frm_mon <= to_mon and to_mon:
                    stat = items.get(r['sid'], (None, None, []))[2]
                    mon_lst = [ f_x[0] for f_x in stat ]
                    for i in range( bisect.bisect_left(mon_lst, frm_mon),  bisect.bisect_right(mon_lst, to_mon) ):
                        s = stat[i]
                        s_qty += s[1]
                        s_price += s[2]
                        s_cost += s[3]
                
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
        wt.writerow(['#ID', 'Name', 'UOM', 'Status', 'Cate', 'Dept', 'OnHand', 'OnOrder', 'T_Qty', 'T_Sale', 'T_Cost', 'Margin', 'Margin%'])
        for r in apg: wt.writerow(map(lambda f_x: unicode(f_x).encode('utf8'), r[:-1]))
        
        self.req.out_headers['content-type'] = 'application/octet-stream'
        self.req.out_headers['content-disposition'] = 'attachment; filename="data.csv"'
        self.req.write( fp.getvalue() )


    def _fn_export2_csv(self):
        rlen, apg_ = self.get_items(0, 0, 0, None, None, 0, 0, 0, 1)
        apg = []
        for r in apg_:
            l_stat = r['l_stat']
            s_mgn = l_stat[1] - l_stat[2]
            apg.append(
                [
                    r['num'],
                    r['jsd']['vends'][0][0],
                    r['jsd']['units'][0][1],
                    r['name'].encode('utf8'),
                    r['unit'][2],
                    r['s_status'] or '',
                    r['s_cate'] or '',
                    r['s_dept'] or '',
                    r['l_qty'][0] and int(r['l_qty'][0]) or '',
                    r['l_qty'][3] and int(r['l_qty'][3]) or '',
                    ]
            )
        
        fp = cStringIO.StringIO()
        wt = csv.writer(fp)
        wt.writerow(['#ID', 'Vend', 'ALU', 'Name', 'UOM', 'Status', 'Cate', 'Dept', 'OnHand', 'OnOrder'])
        for r in apg: wt.writerow(r)
        
        self.req.out_headers['content-type'] = 'application/octet-stream'
        self.req.out_headers['content-disposition'] = 'attachment; filename="data.csv"'
        self.req.write( fp.getvalue() )
