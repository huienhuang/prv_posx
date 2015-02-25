import mysql.connector as MySQL
import config
import thread
import time
import traceback
import sqlanydb

def default_stop_pending(): return 0
stop_pending = default_stop_pending

def open_db(dbs, nz):
    db = dbs.get(nz)
    if db == None:
        if nz == 'mysql':
            dbc = MySQL.connect(**config.mysql)
        elif nz == 'sqlany':
            dbc = sqlanydb.connect(**config.sqlany_pos_server)

        cur = dbc.cursor()
        db = dbs[nz] = (dbc, cur)

    return db

def close_db(dbs, nz):
    db = dbs.get(nz)
    if db != None:
        dbc,cur = db
        try:
            cur.close()
        except:
            pass
        try:
            dbc.close()
        except:
            pass
        dbs[nz] = None


def thread_srv(func, tms=600):
    dbs = {}

    while True:   
        try:
            func( (open_db(dbs, 'mysql')[1], open_db(dbs, 'sqlany')[1]) )
            
        except MySQL.errors.Error, e:
            print "MySQLError", e
            close_db(dbs, 'mysql')
            
        except sqlanydb.Error, e:
            print "sqlanydb.Error", e
            close_db(dbs, 'sqlany')

        except Exception, e:
            print traceback.format_exc()

        time.sleep(tms / 1000.0)

def srv_main(srvs):
    global stop_pending
    try:
        import pysrv
        stop_pending = pysrv.stop_pending
    except Exception, e:
        print e, "fallback -> default_stop_pending"
    
    print __file__, ' > start'

    for s in srvs: thread.start_new_thread(thread_srv, s)
    
    while not stop_pending(): time.sleep(0.2)
    
    print "Done"


