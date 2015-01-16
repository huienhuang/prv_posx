import config
import hashlib
import bisect

DEFAULT_PERM = 1 << config.USER_PERM_BIT['purchasing_mgr']
class RequestHandler(App.load('/advancehandler').RequestHandler):

    def fn_default(self):
        self.req.writefile("po_request.html")