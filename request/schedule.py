import json
import time
import config
import datetime



DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('schedule.html')
    
    
    def fn_get_doc(self):
        d_num = self.req.qsv_ustr('num')
        if not d_num.isdigit(): return
        d_type = int(bool(self.req.qsv_int('type')))
        
        cur = self.cur()
        if d_type:
            cur.execute('select sid,assoc,order_date,global_js from sync_receipts where num=%s and sid_type=0 and (type&0xFF)=0 order by sid desc limit 1', (
                int(d_num),
                )
            )
        else:
            cur.execute('select sid,clerk,sodate,global_js from sync_salesorders where sonum=%s and (status>>4)=0 order by sid desc limit 1', (
                d_num,
                )
            )
        
        row = cur.fetchall()
        if not row: self.req.exitjs({'err': -1, 'err_s': 'doc#%s not found' % (d_num,)})
        sid,assoc,doc_date,gjs = row[0]
        
        gjs = json.loads(gjs)
        company = (gjs.get('customer') or {}).get('company') or ''
        
        js = {
            'type': d_type,
            'sid':str(sid),
            'assoc': assoc,
            'company': company,
            'total': gjs['total'],
            'doc_date': doc_date,
            'sc_rev': 0,
            'sc_date': None,
            'sc_flag': 0
        }
        
        cur.execute('select sc_date,sc_rev,sc_flag from schedule where doc_type=%s and doc_sid=%s', (
            d_type, sid
            )
        )
        row = cur.fetchall()
        if row:
            row = row[0]
            js['sc_date'] = row[0]
            js['sc_rev'] = row[1]
            js['sc_flag'] = row[2]
        
        self.req.writejs(js)
    
    def fn_set_doc(self):
        d_sid = self.req.psv_int('sid')
        d_date = map(int, self.req.psv_ustr('date').split('-'))
        d_date = d_date[0] * 10000 + d_date[1] * 100 + d_date[2]
        d_type = int(bool(self.req.psv_int('type')))
        sc_rev = self.req.psv_int('rev')
        sc_lvl = self.req.psv_int('lvl')
        
        cts = int(time.time())
        
        cur = self.cur()
        if d_type:
            cur.execute('select num from sync_receipts where sid=%s and sid_type=0 and (type&0xFF)=0 order by sid desc limit 1', (
                d_sid,
                )
            )
        else:
            cur.execute('select sonum from sync_salesorders where sid=%s and (status>>4)=0 order by sid desc limit 1', (
                d_sid,
                )
            )
        
        row = cur.fetchall()
        if not row: return
        d_num = row[0][0]
        
        js = json.dumps([self.user_id, self.user_name, cts, d_date, sc_lvl], separators=(',',':'))
        
        if sc_rev == 0:
            cur.execute('insert into schedule values(%s,%s,1,0,%s,%s,%s)', (
                d_date, sc_lvl, d_type, d_sid, js
                )
            )
        else:
            cur.execute("update schedule set sc_date=%s,sc_lvl=%s,sc_rev=sc_rev+1,sc_js=concat(sc_js,',',%s) where doc_type=%s and doc_sid=%s and sc_rev=%s and (sc_date!=%s or sc_lvl!=%s)", (
                d_date, sc_lvl, js, d_type, d_sid, sc_rev, d_date, sc_lvl
                )
            )
            
        rc = cur.rowcount
        if rc <= 0: self.req.exitjs({'err': -2, 'err_s': "doc#%s - can't make any update" % (d_num, )})
        
        
        self.req.exitjs({'err': 0})



