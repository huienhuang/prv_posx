import config
import hashlib
import json
import time
import struct
import socket
import re

CFG = {
    'id': 'SIMPLEINFO_88000007',
    'name': 'Item Info Lookup For Guest',
    'perm_list': [
    ('access', ''),
    ]
}

class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_alu(self):
        self.req.writefile('itemalu.html')
    fn_alu.PERM = 0


