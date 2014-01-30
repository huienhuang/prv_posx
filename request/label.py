import config
import hashlib
import json
import time
import struct
import socket
import re


DEFAULT_PERM = 0x00000000
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        d = {
            'templates': (
                ('5193', '5163 2 x 4'),
                ('5160', '5160 1 x 2 5/8'),
            )
        }
        self.req.writefile('label.html', d)


    def fn_preview(self):
        tmpl = self.req.qsv_int('tmpl')
        self.req.writefile('label_preview_%d.html' % (tmpl,))


