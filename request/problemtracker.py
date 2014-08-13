import config
import hashlib
import json
import time
import struct
import re


ITEM_CASE = {

100: 'Low Stock',

200: 'Wrong Info'


}


DEFAULT_PERM = (1 << config.USER_PERM_BIT['base access']) | (1 << config.USER_PERM_BIT['normal access'])
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        r = {
            'tab_cur_idx' : 2,
            'title': 'Problem Tracker',
            'tabs': [ ('report_a_problem', 'Item'), ]
        }
        self.req.writefile('tmpl_multitabs.html', r)

    def fn_report_a_problem(self):
        r = {}
        
        self.req.writefile('tracker/report_a_problem.html', r)


    def fn_get_items(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            d_users = dict([f_v[:2] for f_v in self.getuserlist()])
            cur.execute('select tid,uid,sid,type,js from tracker where flag=0 order by tid asc limit %d,%d' % (
                        sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                
                apg.append(r[:-1])
        
        cur.execute('select count(*) from deliveryv2')
        rlen = int(cur.fetchall()[0][0])
        
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
        
        