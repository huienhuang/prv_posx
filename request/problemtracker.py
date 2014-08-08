import config
import hashlib
import json
import time
import struct
import re

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
