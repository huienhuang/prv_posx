import os
import config
import cPickle

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
    
    
    
    
    