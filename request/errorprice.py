import json
import os

DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('errorprice.html')
    
    def fn_getpage(self):
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        sb = self.qsv_int('sb')
        sd = self.qsv_int('sd')
        
        if pgsz <= 0 or sidx < 0 or sidx >= eidx or sb < 0: return
        df = self.req.app.app_dir + '/data/errorprice.txt'
        if not os.path.exists(df): return
        d = json.load(open(df, 'rb'))
        
        rpg = {}
        for i in range(sidx, eidx): rpg[i] = []
        
        if d and sb >= 0 and sb < len(d[0]):
            k = 0
            for r in d[sidx * pgsz : eidx * pgsz]:
                rpg[sidx].append(r)
                k += 1
                if k == pgsz:
                    sidx += 1
                    k = 0
            
        rlen = len(d)
        self.req.writejs( {'res':{'len':rlen, 'rpg':rpg}} )
        
    def fn_getrowidx(self):
        kws = self.qsv_int('kws', -1)
        sb = self.qsv_int('sb')
        sd = self.qsv_int('sd')
        if kws < 0 or sb < 0: return
        
        if not kws: return
        df = self.req.app.app_dir + '/data/errorprice.txt'
        if not os.path.exists(df): return
        d = json.load(open(df, 'rb'))
        
        ridx = -1
        if d and sb >= 0 and sb < len(d[0]):
            for i in xrange(len(d)):
                if d[i][0] == kws:
                    ridx = i
                    break
        
        jsn = {'res': {'ridx':ridx}}
        self.req.writejs(jsn)
        
        