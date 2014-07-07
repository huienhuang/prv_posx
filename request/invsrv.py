import json
import time
import config
import re
import datetime


class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('inv_srv.html')
        
