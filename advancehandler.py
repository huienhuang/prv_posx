import os
import config
import cPickle
import re
import json


DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def get_data_file_cached(self, cache_key, file_name):
        als = self.req.app.als
        
        fnz = os.path.join(config.DATA_DIR, file_name)
        if not os.path.exists(fnz): return
        
        mtime, content = als.get(cache_key) or (0, None)
        cur_mtime = os.stat(fnz).st_mtime
        if content and mtime < cur_mtime: content = None
        if not content:
            with open(fnz, 'rb') as fp:
                content = cPickle.load(fp)
            als[cache_key] = (cur_mtime, content)
            
        return content
    
    def get_items_stat(self):
        return self.get_data_file_cached('items_stat', 'items_stat.txt')
    
    def get_customer_report(self):
        return self.get_data_file_cached('customer_report', 'customer_report.txt')
    
    def get_comm_clerks_js(self, ds):
        return self.get_data_file_cached('comm_clerks_js__%s' % (ds,), '%s_comm_clerks.txt' % (ds,))
    
    def get_comm_js(self, ds):
        return self.get_data_file_cached('comm_js__%s' % (ds,), '%s_comm.txt' % (ds,))
    
    
    def get_item(self, item_no):
        cur = self.cur()
        cur.execute('select sid,num,name,detail from sync_items where num=%s', (item_no,))
        rows = cur.fetchall()
        if not rows: return
        row = list(rows[0])
        row[0] = str(row[0])
        row[3] = json.loads(row[3])
        return row

    def get_item_by_sid(self, item_sid):
        cur = self.cur()
        cur.execute('select sid,num,name,detail from sync_items where sid=%s', (item_sid,))
        rows = cur.fetchall()
        if not rows: return
        row = list(rows[0])
        row[0] = str(row[0])
        row[3] = json.loads(row[3])
        return row
    
    regx_kw = re.compile(u'[^ 0-9a-z,]+', re.I|re.M|re.S)
    def search_item(self, kw, mode, num_row=16):
        kws = set(self.regx_kw.sub(u' ', kw).strip().lower().replace(u',', u' ').strip().split(u' '))
        kws.discard(u'')
        if not kws: return
        
        db = self.db()
        cur = db.cur()
        
        sid_lku = {}
        items = []
        if kw.isdigit():
            cur.execute('select i.sid,i.num,i.name,i.detail,u.default_uom_idx from sync_items_upcs u left join sync_items i on (u.sid=i.sid) where u.upc=%d order by i.num asc limit %d' % (int(kw), num_row))
            for x in cur.fetchall():
                sid_lku[ x[0] ] = True
                items.append( [str(x[0]),] + list(x[1:]) )
        
        if mode:
            kw = '+' + u' +'.join([k for k in kws])
        else:
            kw = '+' + u' +'.join([k + '* ' + k for k in kws])
        qs = "select sid,num,name,detail,(match(lookup,name) against (%s in boolean mode) + match(lookup) against (%s in boolean mode)*2) as pos from sync_items where match(lookup,name) against (%s in boolean mode) order by pos desc,num asc limit " + "%d" % (num_row,)
        cur.execute(qs, (kw, kw.replace(u'+', u''), kw))
        k = min(len(items), 2)
        for x in cur.fetchall():
            if sid_lku.has_key(x[0]): continue
            items.append( [str(x[0]),] + list(x[1:4]) + [None] )
            k += 1
            if k >= num_row: break
            
        return items
    
    def search_cust(self, kw, mode, num_row=16):
        kws = set(self.regx_kw.sub(u' ', kw).strip().lower().replace(u',', u' ').strip().split(u' '))
        kws.discard(u'')
        if not kws: return
        
        db = self.db()
        cur = db.cur()
        #kw = db.escape_string('+' + u' +'.join([ len(k) > 2 and not k.isdigit() and k + '*' or k + '* ' + k for k in kws]).encode('utf8'))
        if mode:
            kw = '+' + u' +'.join([k for k in kws])
        else:
            kw = '+' + u' +'.join([k + '* ' + k for k in kws])
        qs = "select sid,name,detail,(match(name,lookup) against (%s in boolean mode) + match(name) against (%s in boolean mode)*2) as pos from sync_customers where match(name,lookup) against (%s in boolean mode) order by pos desc,sid desc limit " + str(num_row)
        #self.out.write(qs)
        cur.execute(qs, (kw, kw.replace(u'+', u''), kw))
        res = [ [str(x[0]),] + list(x[1:]) for x in cur.fetchall()]
        
        return res
    
    
    