import json


DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/request/sys').RequestHandler):
    def fn_default(self):
        data = ((1, 'cash'), (2, 'check'), (3, 'card'))
        self.setconfigv2('payments', json.dumps(data, separators=(',',':')))
        self.req.write('fn_default -> hello++')
        


