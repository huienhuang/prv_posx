import json
import os
import time
import config
import re
import datetime
import winlib
import struct

DEFAULT_PERM = 1 << config.USER_PERM_BIT['sys']
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_mac(self):
        s = {}
        v = self.getconfigv2('allowed_mac_addrs', '')
        if v: s = dict([ (x, [[], 1]) for x in struct.unpack('<' + 'Q' * (len(v) / 8), v) ])
        
        l = winlib.get_arp_list( config.server_network[0], config.server_network[1] )
        for v in l:
            if not v[2]: continue
            m = s.setdefault(v[2], [[], 0])
            m[0].append( (config.ulong2ip(v[0]), v[1]) )
        
        mac_lst = [ (config.ulonglong2mac(k), v) for k,v in s.items() ]
        self.req.writefile( 'mac.html', {'mac_lst':mac_lst} )
    
    def fn_macsave(self):
        mac = [ config.mac2ulonglong(x.replace('-', '').strip()) for x in self.req.psv_ustr('mac').split(',') if x.strip() ]
        mac.sort()
        
        s = ''
        if mac: s = struct.pack('<' + 'Q' * len(mac), *mac)
        
        self.setconfigv2('allowed_mac_addrs', s)
        self.req.writejs( {'res':1} )

