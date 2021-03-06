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
import struct
import const
import boundary
import winlib
import db as mydb


def default_stop_pending(): return 0
stop_pending = default_stop_pending

def get_zone_id(lat, lng):
    idx = winlib.find_boundary(lng, lat)
    if idx < 0:
        return 0
    else:
        return ZONE_IDX_MAP[idx]

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


ZONE_IDX_MAP = []

def main():
    global stop_pending
    try:
        import pysrv
        stop_pending = pysrv.stop_pending
    except Exception, e:
        print e, "fallback -> default_stop_pending"
    
    print __file__, ' > start'
    
    ###
    d_zones = {}
    for i in range(len(const.ZONES)): d_zones[ const.ZONES[i][0] ] = i
    
    b_lst = []
    for b in boundary.BOUNDARY:
        ZONE_IDX_MAP.append( d_zones[ b[0] ] )
        b_lst.append( struct.pack('%dd' % (len(b[2]), ), *b[2]) )
    
    winlib.load_boundary(tuple(b_lst))
    ###
    
    for s in g_srvs: thread.start_new_thread(thread_srv, s)
    
    while not stop_pending(): time.sleep(0.2)
    
    print "Done"


    

################################################


def srv_normal(cur):
    s_ts = int(time.time() * 1000)
    c_id = None
    addrs = {}
    other = {}
    cur.execute('select * from sync_chg where c_type<=16 order by c_id asc')
    for r in cur.fetchall():
        c_id,c_type,c_js = r
        c_js = json.loads(c_js)
            
        if c_type == 1:
            mt_customer(cur, c_js, addrs, other)
        elif c_type == 2:
            mt_receipt(cur, c_js, addrs, other)
        elif c_type == 3:
            mt_salesorder(cur, c_js, addrs, other)
    
    addrs = addrs.items()
    addrs_len = 0
    while addrs:
        cur.executemany('insert ignore into address values(%s,0,0,0,0,0,%s)',
                    [ (base64.b64decode(k), json.dumps({'orig':v}, separators=(',',':'))) for k,v in addrs[:300] ]
        )
        addrs_len += cur.rowcount
        addrs = addrs[300:]
    
    if other.get('inc_schedule_seq', [0])[0]:
        cur.execute('update config set cval=cval+1 where cid=%s', (config.CFG_SCHEDULE_UPDATE_SEQ,))
    
    if c_id != None:
        cur.execute('delete from sync_chg where c_id<=%s and c_type<=16', (c_id,))
        if addrs_len:
            print 'LOC: %d, MS: %d, TS: %s' % (addrs_len, int(time.time() * 1000) - s_ts, str(datetime.datetime.now()))


def srv_location(cur):
    s_ts = int(time.time() * 1000)
    c = 0
    e = 0
    cur.execute('select loc,js from address where flag=0')
    for r in list(cur.fetchall()):
        loc,js = r
        js = json.loads(js)
        res,geo = get_geocoding(js['orig'])
        if res == 1:
            f_addr,lat,lng = geo
            js['addr'] = f_addr
            zone_id = get_zone_id(lat,lng)
            cur.execute('update address set flag=%s,zone_id=%s,lts=%s,lat=%s,lng=%s,js=%s where loc=%s', (
                1, zone_id, int(time.time()), lat, lng, json.dumps(js, separators=(',',':')), loc
                )
            )
            c += 1
        elif res == -1:
            cur.execute('update address set flag=%s,lts=%s where loc=%s', (
                -1, int(time.time()), loc
                )
            )
            e += 1
    if c:
        print 'GEO: (%d, %d), MS: %d, TS: %s' % (c, e, int(time.time() * 1000) - s_ts, str(datetime.datetime.now()))
        
def get_geocoding(addr):
    ret = (0, None)
    
    p = {'address': addr,
         'components': 'country:US',
         'key': config.google_geocoding_api,
         'bounds': '37.7484907197085,-122.3993457802915|37.7511886802915,-122.3966478197085'
    }
    try:
        f = urllib.urlopen('https://maps.googleapis.com/maps/api/geocode/json?' + urllib.urlencode(p))
        js = json.loads(f.read())
        try:
            if js['status'] in ('OK', 'ZERO_RESULTS'):
                if not js['results']: return (-1, None)
                res = js['results'][0]
                loc = res['geometry']['location']
                return (1, (res['formatted_address'], float(loc['lat']), float(loc['lng'])))
        except:
            pass
        time.sleep(35)
        
    except:
        pass
    
    time.sleep(5)
    return ret


g_srvs = [(srv_location, 750), (srv_normal, 750)]


def mt_customer(cur, lst, addrs, other):
    cur.execute('select detail from sync_customers where sid in (%s)' % (
        ','.join(map(str, set([ f_x[0] for f_x in lst ]))),
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

def mt_receipt(cur, lst, addrs, other):
    s_sids = ','.join(map(str, set([ f_x[0] for f_x in lst ])))
    cur.execute('select global_js from sync_receipts where sid_type=0 and sid in (%s)' % (s_sids,))
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
    
    odt = datetime.date.today()
    cdt = odt.year * 10000 + odt.month * 100 + odt.day
    cur.execute('select count(*) from schedule where sc_date>=%d and doc_type=1 and doc_sid in (%s)' % (cdt, s_sids))
    other.setdefault('inc_schedule_seq', [0])[0] += cur.fetchall()[0][0]

def mt_salesorder(cur, lst, addrs, other):
    s_sids = ','.join(map(str, set([ f_x[0] for f_x in lst ])))
    cur.execute('select global_js from sync_salesorders where sid in (%s)' % (s_sids,))
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
                
    odt = datetime.date.today()
    cdt = odt.year * 10000 + odt.month * 100 + odt.day
    cur.execute('select count(*) from schedule where sc_date>=%d and doc_type=0 and doc_sid in (%s)' % (cdt, s_sids))
    other.setdefault('inc_schedule_seq', [0])[0] += cur.fetchall()[0][0]
    

if __name__ == '__main__':
    main()
