import config
import sqlanydb
import db as mydb
import time
import datetime
import sys


__all__ = ["ri", "rf", "rf2", "pos_db", "pos_db_close", "sys_db", "sys_db_close", "set_last_update_ts", "sync", "sync_main", "parse_dt_v1", "parse_dt_v2"]


g_db = {}
g_pos_server = config.sqlany_pos_server

def ri(s): return int(math.floor(float(s)))
def rf(s, n=0): return config.round_ex(float(s), n)
def rf2(s): return rf(s, 2)

def pos_db():
    c = g_db.get('pos')
    if c != None: return (g_db.get('pos_cur'), g_db.get('pos_sur'))
    c = g_db['pos'] = sqlanydb.connect(**g_pos_server)
    cur = g_db['pos_cur'] = c.cursor()
    sur = g_db['pos_sur'] = c.cursor()
    return (cur, sur)

def pos_db_close():
    c = g_db.get('pos')
    if c == None: return
    try:
        c.close()
    except:
        pass
    g_db['pos'] = g_db['pos_cur'] = g_db['pos_sur'] = None
    
def sys_db():
    c = g_db.get('sys')
    if c != None: return c
    c = g_db['sys'] = mydb.db_default()
    return c

def sys_db_close():
    c = g_db.get('sys')
    if c == None: return
    try:
        c.close()
    except:
        pass
    g_db['sys'] = None
    
def get_last_cj_id():
    return config.get_config_(sys_db(), config.cid__sync_last_cj_id)

def set_last_cj_id(cj_id):
    config.set_config_(sys_db(), config.cid__sync_last_cj_id, cj_id)

def set_last_update_ts():
    config.set_config_(sys_db(), config.cid__sync_last_update, int(time.time()))

def get_max_cj_id():
    cur,sur = pos_db()
    sur.execute('select max(id) from changejournal')
    return sur.fetchall()[0][0] or 0

def get_cj_data(last_cj_id, max_cj_id):
    cur,sur = pos_db()
    sur.execute('select distinct tablename,docsid from changejournal where id > %d and id <= %d' % (
        last_cj_id, max_cj_id
    ))
    return sur.fetchall()

def get_max_fs_id():
    cur,sur = pos_db()
    sur.execute('select max(messageid) from logmessage')
    return sur.fetchall()[0][0] or 0

def get_fs_data(last_fs_id, max_fs_id):
    cur,sur = pos_db()
    sur.execute("select logtext from logmessage where messageid > %d and messageid <= %d and logtype=4" % (
        last_fs_id, max_fs_id
    ))
    cids = {}
    for r in sur.rows():
        t = r[0]
        if not t: continue
        i = t.find('#qbpos:command.customer.')
        if i < 0: continue
        t = t[i + 24:]
        i = t.find('#')
        if i < 0: continue
        t = t[:i]
        try:
            sid = int(t)
        except Exception:
            continue
        cids[sid] = True
    
    return [ ('customer', x) for x in cids.keys() ]

def get_last_fs_id():
    return config.get_config_(sys_db(), config.cid__sync_last_fs_id)

def set_last_fs_id(fs_id):
    config.set_config_(sys_db(), config.cid__sync_last_fs_id, fs_id)

g_sync_tp = (
    ['CJ', get_max_cj_id, get_cj_data, get_last_cj_id, set_last_cj_id, None, True],
    ['FS', get_max_fs_id, get_fs_data, get_last_fs_id, set_last_fs_id, None, False]
)

def fs_to_cj(data):
    data = [(f_x[1],) for f_x in data if f_x[0] == 'customer']
    if not data: return
    n = len(data)
    
    dbc = sqlanydb.connect(**g_pos_server)
    cur = dbc.cursor()
    cur.execute("SET TEMPORARY OPTION CONNECTION_AUTHENTICATION='Company=Intuit Inc.;Application=QuickBooks Point of Sale;Signature=000fa55157edb8e14d818eb4fe3db41447146f1571g7262d341128bbd2768e586a0b43d5568a6bb52cc'")
    
    try:
        while data:
            cur.executemany("insert into changejournal values(default,'Customer',?,1,now(),'POSX', '-1')", data[:500])
            data = data[500:]
        cur.execute('commit')
        cur.close()
    finally:
        dbc.close()

    print 'fs_to_cj: N(%d)' % (n, )

def sync(sync_cbs, mode):
    for tp in g_sync_tp:
        ts = time.time()
        ct = 0
        
        name,get_max_id,get_data,get_last_id,set_last_id,last_id,init_call = tp
        max_id = get_max_id()
        
        data = None
        if not mode:
            if last_id == None: last_id = tp[5] = get_last_id()
            if last_id >= max_id: continue
            data = get_data(last_id, max_id)
            
        if mode and init_call or data:
            if name == 'FS':
                fs_to_cj(data)
                ct += len(data)
            else:
                for cb in sync_cbs:
                    ct += cb[1](data, mode)
        
        set_last_id(max_id)
        tp[5] = max_id
        
        if ct:
            print "%s > ts: %s, %s < rng <= %d, ms: %s" % (
                name,
                str(datetime.datetime.now()),
                last_id,
                max_id,
                int( (time.time() - ts) * 1000 )
            )


def sync_main(sync_cb):
    mode = len(sys.argv) > 1 and int(sys.argv[1]) or 0
    sync([sync_cb], mode)



def parse_dt_v1(s):
    try:
        ts = s and int(time.mktime(time.strptime(s.split('.')[0], '%Y-%m-%d %H:%M:%S'))) or 0
    except:
        ts= 0
    return ts


def parse_dt_v2(s):
    try:
        ts = s and int(time.mktime(time.strptime(s, '%Y-%m-%d'))) or 0
    except:
        ts= 0
    return ts