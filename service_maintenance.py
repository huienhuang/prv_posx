import time
import datetime
import json
import traceback
import thread
import base64
import mysql.connector as MySQL
import config
import data_helper
import urllib


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


    

################################################


def srv_normal(cur):
    c_id = None
    addrs = {}
    cur.execute('select * from sync_chg where c_type<=16 order by c_id asc')
    for r in cur.fetchall():
        c_id,c_type,c_js = r
        c_js = json.loads(c_js)
            
        if c_type == 1:
            mt_customer(cur, c_js, addrs)
        elif c_type == 2:
            mt_receipt(cur, c_js, addrs)
        elif c_type == 3:
            mt_salesorder(cur, c_js, addrs)
    
    addrs = addrs.items()
    addrs_len = len(addrs)
    while addrs:
        cur.executemany('insert ignore into address values(%s,0,0,0,0,%s)',
                    [ (base64.b64decode(k), json.dumps({'orig':v}, separators=(',',':'))) for k,v in addrs[:300] ]
        )
        addrs = addrs[300:]
    
    if c_id != None:
        cur.execute('delete from sync_chg where c_id<=%s and c_type<=16', (c_id,))
        print "Locations: %d" % (addrs_len, )


def srv_location(cur):
    cur.execute('select loc,lts,js from address where flag=0')
    for r in list(cur.fetchall()):
        loc,lts,js = r
        if lts and lts + 3 > int(time.time()): continue
        
        js = json.loads(js)
        res,geo = get_geocoding(js['orig'])
        lat = lng = 0
        f_addr = None
        cts = int(time.time())
        
        if res == 1:
            f_addr,lat,lng = geo
            js['addr'] = f_addr
            cur.execute('update address set flag=%s,lts=%s,lat=%s,lng=%s,js=%s where loc=%s', (
                res, cts, lat, lng, json.dumps(js, separators=(',',':')), loc
                )
            )
        else:
            cur.execute('update address set flag=%s,lts=%s where loc=%s', (
                res, cts, loc
                )
            )
            
        print res,geo
        
        
def get_geocoding(addr):
    ret = (0, None)
    
    p = {'address': addr, 'components': 'country:US'}
    try:
        f = urllib.urlopen('http://maps.googleapis.com/maps/api/geocode/json?' + urllib.urlencode(p))
        js = json.loads(f.read())
        if js['status'] != 'OK': return ret
        if not js['results']: return (-1, None)
        res = js['results'][0]
        loc = res['geometry']['location']
        return (1, (res['formatted_address'], float(loc['lat']), float(loc['lng'])))
        
    except Exception, e:
        print e
    
    return ret


g_srvs = [(srv_location, 750), (srv_normal, 750)]


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

def mt_receipt(cur, lst, addrs):
    cur.execute('select global_js from sync_receipts where sid_type=0 and sid in (%s)' % (
        ','.join(map(str, set([ f_x[0] for f_x in lst if not f_x[1] ]))),
    ))
    for r in cur.fetchall():
        jsd = json.loads(r[0])
        
        if jsd['customer'] and jsd['customer']['loc'] != None:
            cust = jsd['customer']
            loc = cust['loc']
            if not addrs.has_key(loc):
                addrs[loc] = u','.join( data_helper.unify_location(
                    (cust['addr1'], cust['city'], cust['state'], cust['zip'])
                    )
                )

        if jsd['shipping'] and jsd['shipping']['loc'] != None:
            cust = jsd['shipping']
            loc = cust['loc']
            if not addrs.has_key(loc):
                addrs[loc] = u','.join( data_helper.unify_location(
                    (cust['addr1'], cust['city'], cust['state'], cust['zip'])
                    )
                )

def mt_salesorder(cur, lst, addrs):
    cur.execute('select global_js from sync_salesorders where sid in (%s)' % (
        ','.join(map(str, set([ f_x[0] for f_x in lst if not f_x[1] ]))),
    ))
    for r in cur.fetchall():
        jsd = json.loads(r[0])
        
        if jsd['customer'] and jsd['customer']['loc'] != None:
            cust = jsd['customer']
            loc = cust['loc']
            if not addrs.has_key(loc):
                addrs[loc] = u','.join( data_helper.unify_location(
                    (cust['addr1'], cust['city'], cust['state'], cust['zip'])
                    )
                )

        if jsd['shipping'] and jsd['shipping']['loc'] != None:
            cust = jsd['shipping']
            loc = cust['loc']
            if not addrs.has_key(loc):
                addrs[loc] = u','.join( data_helper.unify_location(
                    (cust['addr1'], cust['city'], cust['state'], cust['zip'])
                    )
                )


if __name__ == '__main__':
    main()
