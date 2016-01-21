from sync_helper import *
import sys
import json
import time
import cPickle
import config

def sync_vendors(cj_data, mode=0):
    cur,sur = pos_db()
    mdb = sys_db()
    
    if not mode:
        sids = [ str(x[1]) for x in cj_data if x[0] and x[0].lower() == 'vendor' ]
        if not sids: return 0

    cur.execute('select company,sid from vendor where datastate=0')
    vendors = [ ((v[0] or '').lower().strip(), v[1]) for v in cur.fetchall() ]
    vendors.sort()
    
    config.set_configv2_(mdb, 'vendors', cPickle.dumps(vendors, 1))
    
    print 'sync_vendors: L(%d)' % (len(vendors), )
    return len(vendors)


g_sync_cb = ('vendors', sync_vendors)

if __name__ == '__main__':
    #sync_vendors(None, 1)
    sync_main(g_sync_cb)

