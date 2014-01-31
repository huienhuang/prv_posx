import config
import hashlib
import json
import time
import struct
import socket
import re


DEFAULT_PERM = 0x00000000
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_alu(self):
        self.req.writefile('itemalu.html')

