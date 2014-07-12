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
        if not row: self.req.exitjs({'err': -1, 'err_s': 'document #%s not found' % (d_num,)})
        sid,assoc,doc_date,gjs = row[0]
        
        gjs = json.loads(gjs)
        company = (gjs.get('customer') or {}).get('company') or ''
        
        recs = []
        js = {
            'type': d_type,
            'sid':str(sid),
            'assoc': assoc,
            'company': company,
            'total': gjs['total'],
            'recs': recs
        }
        
        cur.execute('select sc_id,sc_date,sc_rev,sc_flag,sc_note from schedule where doc_type=%s and doc_sid=%s order by sc_id asc', (
            d_type, sid
            )
        )
        nzs = cur.column_names
        for r in cur.fetchall():
            r = dict(zip(nzs, r))
            r['sc_prio'] = (r['sc_flag'] & 0xF) - 1
            recs.append(r)
        
        self.req.writejs(js)
    
    def fn_set_doc(self):
        d_sid = self.req.psv_int('sid')
        
        d_date = map(int, self.req.psv_ustr('date').split('/'))
        d_date = datetime.date(d_date[2], d_date[0], d_date[1])
        if d_date < datetime.date.today(): self.req.exitjs({'err': -9, 'err_s': "Invalid Date"})
        d_date = d_date.year * 10000 + d_date.month * 100 + d_date.day
        
        d_type = int(bool(self.req.psv_int('type')))
        rev = self.req.psv_int('rev')
        prio = min(max(-1, self.req.psv_int('prio')), 2) + 1
        sc_id = self.req.psv_int('sc_id')
        note = self.req.psv_ustr('note')[:128].strip()
        
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
        
        if sc_id == 0:
            cur.execute('insert into schedule values(null,%s,1,%s,%s,%s,%s)', (
                d_date, prio, d_type, d_sid, note
                )
            )
        else:
            cur.execute("select sc_date,sc_flag from schedule where sc_id=%s and sc_rev=%s", (
                sc_id, rev
                )
            )
            row = cur.fetchall()
            if not row: self.req.exitjs({'err': -3, 'err_s': "document #%s - record #%s - can't find the record" % (d_num, sc_id)})
            old_sc_date,old_sc_flag = row[0]
            if old_sc_date == d_date and (old_sc_flag & 0xF) == prio: self.req.exitjs({'err': -2, 'err_s': "document #%s - record #%s - nothing changed" % (d_num, sc_id)})
            
            cur.execute("update schedule set sc_rev=sc_rev+1,sc_date=%s,sc_flag=%s where sc_id=%s and sc_rev=%s", (
                d_date, (old_sc_flag & ~0xF) | prio, sc_id, rev
                )
            )
            
        rc = cur.rowcount
        if rc <= 0:
            self.req.exitjs({'err': -2, 'err_s': "document #%s - can't make any update" % (d_num, )})
        else:
            pass
            
        self.req.exitjs({'err': 0})

