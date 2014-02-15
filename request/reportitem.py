import config
import hashlib
import json
import bisect
import const


DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        r = {'const':const}
        self.req.writefile('report_item_sale.html', r)
        
        
    def fn_get_items(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        frm_mon = self.qsv_int('frm_mon')
        to_mon = self.qsv_int('to_mon')
        status = self.qsv_int('status')
        dept = self.qsv_ustr('dept')
        cate = self.qsv_ustr('cate')
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            items = self.get_items_sale_stats()
            for sid,item in items.items():
                if status and status != item['status']: continue
                
                
            
            
            cur.execute('select sid,num,name,detail from sync_items order by num asc,sid asc limit %d,%d' % (
                        sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                d = json.loads(r[3])
                qty = d['qty']
                
                stat = stats.get(r[0]) or []
                s_qty = 0
                s_price = 0
                s_cost = 0
                mon_lst = [ f_x[0] for f_x in stat ]
                for i in range( bisect.bisect_left(mon_lst, frm_mon),  bisect.bisect_right(mon_lst, to_mon) ):
                    s = stat[i]
                    s_qty += s[1]
                    s_price += s[2]
                    s_cost += s[3]
                
                s_mgn = s_price - s_cost
                apg.append(
                    [
                    r[1],
                    r[2],
                    qty[0] and int(qty[0]),
                    qty[3] and int(qty[3]),
                    s_qty and int(s_qty) or '',
                    s_price and '%0.2f' % (s_price,) or '',
                    s_cost and '%0.2f' % (s_cost,) or '',
                    s_mgn and '%0.2f' % (s_mgn,) or '',
                    s_price and '%0.2f%%' % (s_mgn * 100 / s_price,) or '',
                    ]
                )
        
        cur.execute('select count(*) from sync_items')
        rlen = int(cur.fetchall()[0][0])
        
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
        
        