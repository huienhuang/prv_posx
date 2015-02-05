import config
import hashlib
import bisect

DEFAULT_PERM = 1 << config.USER_PERM_BIT['purchasing_mgr']
class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        tabs = [('PO', 'PO'), ('View', 'VIEW')]
        r = {
            'tab_cur_idx' : 2,
            'title': 'PO REQUEST',
            'tabs': tabs
        }
        self.req.writefile('tmpl_multitabs.html', r)


    def fn_po(self):
        self.req.writefile('purchasing/po_list.html')
        
    def fn_view(self):
        self.req.writefile('purchasing/po_request.html')
    
    
    def fn_save(self):
        pid = self.req.psv_int('pid')
        desc = self.req.psv_ustr('desc')
        pjs = [ (int(f_x[0]), int(f_x[1]), unicode(f_x[2])) for f_x in self.req.psv_js('pjs') ]
         
        cur = self.cur()
        if pid:
            if not pjs:
                cur.execute('delete from po where pid=%s', (pid,))
            else:
                cur.execute('insert into')
        
        
        
        
    
    