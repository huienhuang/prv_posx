import config
import _mysql
import sqlanydb
import mysql.connector

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
    return sqlanydb.connect(**config.sqlany_qb)

def db_pos():
    return sqlanydb.connect(**config.sqlany_pos)

def db_mdb():
    return mysql.connector.connect(**config.mysql)
