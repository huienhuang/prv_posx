from sync_helper import *
import sys
import json
import time
import cPickle
import config

def sync_departments(cj_data, mode=0):
    cur,sur = pos_db()
    mdb = sys_db()
    
    if not mode:
        sids = [ str(x[1]) for x in cj_data if x[0] and x[0].lower() == 'department' ]
        if not sids: return 0

    cur.execute('select deptname,sid from department where datastate=0')
    depts = [ ((v[0] or '').lower().strip(), v[1]) for v in cur.fetchall() ]
    depts.sort()
    
    config.set_configv2_(mdb, 'departments', cPickle.dumps(depts, 1))
    
    print 'sync_departments: L(%d)' % (len(depts), )
    return len(depts)


g_sync_cb = ('departments', sync_departments)

if __name__ == '__main__':
    #sync_departments(None, 1)
    sync_main(g_sync_cb)

