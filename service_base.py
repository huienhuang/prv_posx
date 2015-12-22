import mysql.connector as MySQL
import config
import thread
import time
import traceback
import db as mydb


def default_stop_pending(): return 0
stop_pending = default_stop_pending


def open_db():
    return mydb.db_mdb()

def close_db(dbc):
    dbc.close()

def thread_srv(func, tms=600):
    dbc = cur = None
    while True:   
        try:
            if dbc == None:
                dbc = open_db()
                cur = dbc.cursor()
                
            func(cur)
            
        except MySQL.errors.Error, e:
            print "MySQLError", e
            try:
                if cur != None: cur.close()
            except:
                pass
            if dbc != None: close_db(dbc)
            dbc = cur = None
            
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


