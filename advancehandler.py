import os
import config
import cPickle

DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def get_items_sale_stats(self):
        als = self.req.app.als
        
        fnz = os.path.join(config.DATA_DIR, 'items_sale_stats.txt')
        if not os.path.exists(fnz): return
        
        mtime, stats = als.get('items_sale_stats') or (0, None)
        cur_mtime = os.stat(fnz).st_mtime
        if stats and mtime < cur_mtime: stats = None
        if not stats:
            stats = cPickle.load( open(fnz, 'rb') )
            als['items_sale_stats'] = (cur_mtime, stats)
            
        return stats
    
