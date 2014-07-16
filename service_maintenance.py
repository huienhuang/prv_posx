import time
import datetime
import json
import traceback
import thread
import base64
import mysql.connector as MySQL
import config
import data_helper


def default_stop_pending(): return 0
try:
    import pysrv
    stop_pending = pysrv.stop_pending
except Exception, e:
    stop_pending = default_stop_pending


def open_db():
    return MySQL.connect(**config.mysql)

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

def main():
    print __file__, ' > start'
    
    for s in g_srvs: thread.start_new_thread(thread_srv, s)
    
    while not stop_pending(): time.sleep(0.2)
    
    print "Done"

if __name__ == '__main__':
    main()
    

################################################


def srv_normal(cur):
    while True:
        c_id = None
        addrs = {}
        cur.execute('select * from sync_chg where c_type<=16 order by c_id asc limit 32')
        for r in cur.fetchall():
            c_id,c_type,c_js = r
            c_js = json.loads(c_js)
            
            if c_type == 1:
                mt_customer(cur, c_js, addrs)
            elif c_type == 2:
                mt_receipt(cur, c_js, addrs)
            elif c_type == 3:
                mt_salesorder(cur, c_js, addrs)
        
        if c_id == None:
            break
        else:
            cur.execute('delete from sync_chg where c_id<=%s and c_type<=16', (c_id,))


def srv_location(cur):
    cur.execute('select h0,h1,c0,js from address where ready=0')
    for r in cur.fetchall():
        h0,h1,c0,js = r
        
        
    
g_srvs = [(srv_location, 600), (srv_normal, 600)]

def mt_customer(cur, lst, addrs):
    
    cur.execute('select detail from sync_customers where sid in (%s)' % (
        ','.join(map(str, set([ f_x[0] for f_x in lst if not f_x[1] ]))),
    ))
    for r in cur.fetchall():
        jsd = json.loads(r[0])
        
        loc = jsd['loc']
        if loc != None:
            if not addrs.has_key(loc):
                addrs[loc] = u','.join( data_helper.unify_location(
                    (jsd['address1'], jsd['city'], jsd['state'], jsd['zip'])
                    )
                )
                
                