import time
import datetime
import math
import sqlanydb
import sys
import traceback
import _mysql_exceptions
from sync_helper import *

g_sync_md = (
    'sync_items_hist',
    'sync_items',
    'sync_customers',
    'sync_receipts',
    'sync_salesorders',
    'sync_purchaseorders',
    'sync_vouchers'
)

g_quit = 0
g_sync_cbs = []

def default_stop_pending(): return 0

def main():
    try:
        import pysrv
        stop_pending = pysrv.stop_pending
    except Exception, e:
        print e, "fallback -> default_stop_pending"
        stop_pending = default_stop_pending
    
    print __file__, ' > start'
    
    for md in g_sync_md:
        m = __import__(md)
        g_sync_cbs.append(getattr(m, 'g_sync_cb'))
    
    uts = lts = int( time.time() * 1000 )
    tms = 1500
    ums = tms * 3
    while not stop_pending():
        if int( time.time() * 1000 ) - lts < tms:
            time.sleep(0.2)
            continue
        
        try:
            sync(g_sync_cbs, 0)
            
            if int( time.time() * 1000 ) - uts >= ums:
                set_last_update_ts()
                uts = int( time.time() * 1000 )
            
        except sqlanydb.Error, e:
            print "sqlanydb.Error", e
            pos_db_close()
            
        except _mysql_exceptions.MySQLError, e:
            print "MySQLError", e
            sys_db_close()
            
        except Exception, e:
            print traceback.format_exc()

        lts = int( time.time() * 1000 )

    print "Done"

if __name__ == '__main__':
    main()
