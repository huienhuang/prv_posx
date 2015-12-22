import config
import sqlanydb
import mysql.connector

try:
    import _mysql
except:
    pass

def db_default():
    c = config.mysql
    d = _mysql.connect(c['host'], c['user'], c['passwd'], c['db'])
    d.set_character_set(c['charset'])
    return d

def chk_default(c):
    res = True
    try:
        c.query('select 1')
        c.use_result()
    except:
        res = False
        
    return res

def db_qb():
    cfg = config.sqlany_qb.copy()
    dd = open(cfg['dbf'] + '.ND', 'rb').read()
    nd = dict([ f_x.strip().split('=', 2) for f_x in dd[dd.find('[NetConnect]') + 12:].strip().split('\n') if f_x.strip()])

    del cfg['dbf']
    cfg['links'] = 'tcpip(host=%s:%s;DoBroadcast=None)' % (cfg['ServerIp'], cfg['ServerPort'])
    cfg['ServerName'] = cfg['EngineName']
    cfg['dbn'] = cfg['FileConnectionGuid']

    return sqlanydb.connect(**cfg)

def db_pos():
    return sqlanydb.connect(**config.sqlany_pos)

def db_mdb():
    return mysql.connector.connect(**config.mysql)
