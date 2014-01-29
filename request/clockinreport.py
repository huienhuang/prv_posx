import config
import hashlib
import json

DEFAULT_PERM = 1 << config.USER_PERM_BIT['time']
class RequestHandler(App.load('/basehandler').RequestHandler):
    def fn_default(self):
        d = {'userlist': self.getuserlist()}
        self.req.writefile('clockinreport.html', d)
    
    def fn_timelist(self):
        uid = self.qsv_int('uid')
        fts = self.qsv_int('fts')
        tts = self.qsv_int('tts')
        
        jso = []
        if not uid:
            db = self.db()
            cur = db.cur()
            cur.execute("select user_id, user_name, cur_in_ts, cur_out_ts from user where user_id != 1 order by user_name asc")
            jso = cur.fetchall()
        
        elif fts and tts:
            db = self.db()
            cur = db.cur()
            cur.execute("select in_ts,out_ts from time where user_id = %d and in_ts >= %d and in_ts < %d order by in_ts desc" % (uid, fts, tts))
            jso = cur.fetchall()
                
        self.req.writejs( {'res': jso, 'uid': uid} )
        
