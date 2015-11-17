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
        if nz == 'posx':
            print "MYSQL",
            dbc = MySQL.connect(**config.mysql)
            cur = dbc.cursor()
            print 'Connected'

        elif nz == 'pos':
            print "SQLANY(POS)",
            dbc = sqlanydb.connect(**config.sqlany_pos)
            cur = dbc.cursor()
            cur.execute("SET TEMPORARY OPTION CONNECTION_AUTHENTICATION='Company=Intuit Inc.;Application=QuickBooks Point of Sale;Signature=000fa55157edb8e14d818eb4fe3db41447146f1571g7262d341128bbd2768e586a0b43d5568a6bb52cc'")
            #cur.execute("SET TEMPORARY OPTION isolation_level = 1;")
            print 'Connected'

        elif nz == 'qb':
            print "SQLANY(QB)",
            dbc = sqlanydb.connect(**config.sqlany_qb)
            cur = dbc.cursor()
            #cur.execute("SET TEMPORARY OPTION isolation_level = 1;")
            print 'Connected'

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
    def get_cur(nz): return open_db(dbs, nz)[1]

    while True:
        try:
            func(get_cur)

        except MySQL.errors.Error, e:
            print "MySQLError", e
            close_db(dbs, 'posx')
            
        except sqlanydb.Error, e:
            print "sqlanydb.Error", e
            close_db(dbs, 'pos')
            close_db(dbs, 'qb')

        except:
            close_db(dbs, 'pos')
            close_db(dbs, 'qb')
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


