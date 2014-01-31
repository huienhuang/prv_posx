import json
import os
import time
import config
import datetime

DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.write('item_info.html')
    
    
    