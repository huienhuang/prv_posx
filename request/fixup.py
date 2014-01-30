import config
import hashlib
import json
import time
import datetime

DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('fixup.html')
        
    def fn_get_inconsistent_customers(self):
        ret = {'res':{'len':0, 'apg':[]}}

        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select SQL_CALC_FOUND_ROWS name,detail,sid from sync_customers where flag!=0 order by sid desc limit %d,%d' % (
                sidx * pgsz, (eidx - sidx) * pgsz
                )
            )
            for r in cur.fetchall():
                name,details,sid = r
                details = json.loads(details)
                r = (name, ', '.join(details.get('incon', [])), str(sid))
                apg.append(r)
        
            cur.execute('select FOUND_ROWS()')
            
        else:
            cur.execute('select count(*) from sync_customers where flag!=0')
            
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
        
        