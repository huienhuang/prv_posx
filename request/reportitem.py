import config
import hashlib
import json
import cPickle
import bisect
import const
import csv
import cStringIO

DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        r = {'const':const}
        self.req.writefile('report_item_sale.html', r)
        
    def get_items(self, frm_mon, to_mon, status, dept_s, cate_s, sidx, eidx, pgsz, mode=0):
        where = []
        if status: where.append('status=%d' % (status,))
        
        l_depts = cPickle.loads(self.getconfigv2('departments'))
        if dept_s or cate_s:
            d_depts = dict(l_depts)
            if dept_s:
                s_dept = set()
                for dept in dept_s.split('|'):
                    deptsid = d_depts.get(dept.strip().lower())
                    if deptsid == None: continue
                    s_dept.add(deptsid)
            else:
                s_dept = []
                for dept in const.ITEM_D_CATE.get(cate_s.lower()) or []:
                    deptsid = d_depts.get(dept.strip().lower())
                    if deptsid == None: continue
                    s_dept.append(deptsid)
            
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
            for r in cur:
                jsd = json.loads(r[5])
                unit = jsd['units'][ jsd['default_uom_idx'] ]
                if not unit[3]: unit = jsd['units'][0]
                
                l_qty = jsd['qty']
                s_qty = 0
                s_price = 0
                s_cost = 0
                
                if frm_mon <= to_mon and to_mon:
                    stat = items.get(r[0], (None, None, []))[2]
                    mon_lst = [ f_x[0] for f_x in stat ]
                    for i in range( bisect.bisect_left(mon_lst, frm_mon),  bisect.bisect_right(mon_lst, to_mon) ):
                        s = stat[i]
                        s_qty += s[1]
                        s_price += s[2]
                        s_cost += s[3]
                
                if unit[3] != 1:
                    s_qty /= unit[3]
                    l_qty = map(lambda f_x: f_x / unit[3], l_qty)
                
                dept = d_r_depts.get(r[4])
                cate = const.ITEM_D_DEPT.get(dept)
                s_mgn = s_price - s_cost
                apg.append(
                    [
                    r[1],
                    r[2],
                    unit[2],
                    d_r_status.get(r[3]) or '',
                    cate or '',
                    dept or '',
                    l_qty[0] and int(l_qty[0]) or '',
                    l_qty[3] and int(l_qty[3]) or '',
                    s_qty and int(s_qty) or '',
                    s_price and '%0.2f' % (s_price,) or '',
                    s_cost and '%0.2f' % (s_cost,) or '',
                    s_mgn and '%0.2f' % (s_mgn,) or '',
                    s_price and '%0.2f%%' % (s_mgn * 100 / s_price,) or '',
                    str(r[0])
                    ]
                )
                
            cur.execute('select FOUND_ROWS()')
            
        else:
            cur.execute('select count(*) from sync_items'+where)
            
        rlen = int(cur.fetchall()[0][0])
    
        return (rlen, apg)
    
    def fn_get_items(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        frm_mon = self.qsv_int('frm_mon')
        to_mon = self.qsv_int('to_mon')
        status = self.qsv_int('status')
        dept_s = self.qsv_str('dept')
        cate_s = self.qsv_str('cate')
        
        rlen, apg = self.get_items(frm_mon, to_mon, status, dept_s, cate_s, sidx, eidx, pgsz)
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
    
    def fn_export_csv(self):
        js = self.req.psv_js('js')
        frm_mon = js['frm_mon'].isdigit() and int(js['frm_mon']) or 0
        to_mon = js['to_mon'].isdigit() and int(js['to_mon']) or 0
        status = js['status'].isdigit() and int(js['status']) or 0
        dept_s = js['dept'].strip()
        cate_s = js['cate'].strip()
        
        rlen, apg = self.get_items(frm_mon, to_mon, status, dept_s, cate_s, 0, 0, 0, 1)
        
        fp = cStringIO.StringIO()
        wt = csv.writer(fp)
        wt.writerow(['#ID', 'Name', 'UOM', 'Status', 'Cate', 'Dept', 'OnHand', 'OnOrder', 'T_Qty', 'T_Sale', 'T_Cost', 'Margin', 'Margin%'])
        for r in apg: wt.writerow(r[:-1])
        
        self.req.out_headers['content-type'] = 'application/octet-stream'
        self.req.out_headers['content-disposition'] = 'attachment; filename="data.csv"'
        self.req.write( fp.getvalue() )
        