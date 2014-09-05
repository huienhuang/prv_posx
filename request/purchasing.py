import config
import hashlib


DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/basehandler').RequestHandler):

    def fn_default(self):
        r = {
            'tab_cur_idx' : 2,
            'title': 'Purchasing',
            'tabs': [ ('cost_n_price_tool', 'Cost & Price Tool'), ]
        }
        self.req.writefile('tmpl_multitabs.html', r)
        
        
    def fn_cost_n_price_tool(self):
        self.req.writefile('purchasing/cost_n_price_tool.html')
    
    