import config
import hashlib
import json
import time
import struct
import socket

DEFAULT_PERM = 0x00000000
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        #self.req.writefile('clockin.html')
        self.req.redirect('clockinv2')
        
        
    def fn_getstate(self):
        seq = self.qsv_int('seq', 0)
        cid = config.cid_user_update_seq
        
        sta = {}
        nzs = []
        
        db = self.db()
        cur = db.cur()
        
        cur_seq = self.getconfig(cid)
        if cur_seq > 0:
            qs = 'select user_id,cur_in_ts,cur_out_ts'
            if cur_seq > seq: qs += ',user_name'
            qs += ' from user where user_id != 1'
            if cur_seq > seq:
                qs += ' order by user_name asc, user_id asc'
            else:
                qs += ' order by user_id asc'
            cur.execute(qs)
            
            cts = int(time.time())
            for r in cur.fetchall():
                userid, in_ts, out_ts = r[:3]
                
                s = 0
                if out_ts:
                    if int(in_ts / 86400) == int(cts / 86400):
                        s = 2
                elif in_ts:
                    s = 1
                    
                if cur_seq > seq: nzs.append( [userid, r[3]] )
                sta[ str(userid) ] = [s, in_ts]
                
                
        self.req.writejs( {'res': sta, 'nzs': nzs, 'seq': cur_seq} )
    
    def fn_setstate(self):
        rip = self.environ.get('REMOTE_ADDR', '')
        rip = rip and struct.unpack("<i", socket.inet_aton(rip))[0] or 0
        uid = self.qsv_int('uid', 0)
        out = self.qsv_int('out', 0)
        
        ar = 0
        if uid:
            ts = int(time.time())
            db = self.db()
            cur = db.cur()
            if out:
                qs = "update user set cur_out_ts = %d where cur_in_ts != 0 and cur_out_ts = 0 and user_id = %d limit 1" % (ts, uid)
                cur.execute(qs)
                ar = int(cur.rowcount > 0)
                if ar:
                    qs = "update time set out_ts = %d,out_ip = %d where user_id = %d and in_ts = (select cur_in_ts from user where user_id=%d limit 1) and out_ts = 0 limit 1" % (
                        ts, rip, uid, uid)
                    cur.execute(qs)
            else:
                qs = "update user set cur_in_ts = %d, cur_out_ts = 0 where (cur_in_ts = 0 or cur_out_ts != 0) and user_id = %d limit 1" % (ts, uid)
                cur.execute(qs)
                ar = int(cur.rowcount > 0)
                if ar:
                    qs = "insert into time values (%d,%d,0,%d,0)" % (
                        uid, ts, rip)
                    cur.execute(qs)
        
        self.req.writejs( {'res': ar} )
        
