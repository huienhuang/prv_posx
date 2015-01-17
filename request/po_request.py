import config
import hashlib
import bisect

DEFAULT_PERM = 1 << config.USER_PERM_BIT['purchasing_mgr']
class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        tabs = [('PO', 'PO'), ('View', 'VIEW')]
        r = {
            'tab_cur_idx' : 3,
            'title': 'PO REQUEST',
            'tabs': tabs
        }
        self.req.writefile('tmpl_multitabs.html', r)


    def fn_po(self):
        self.req.writefile('purchasing/po_list.html')
        
    def fn_view(self):
        self.req.writefile('purchasing/po_request.html')
    