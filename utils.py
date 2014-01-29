
def ip2ulong(s):
    p = s.split('.')
    return (int(p[3]) << 24) | (int(p[2]) << 16) | (int(p[1]) << 8) | int(p[0])

def ulong2ip(u):
    return '%d.%d.%d.%d' % (u & 0xFF, (u >> 8) & 0xFF, (u >> 16) & 0xFF, (u >> 24) & 0xFF)

def mac2ulonglong(s):
    return (int(s[10:12], 16) << 40) | (int(s[8:10], 16) << 32) | (int(s[6:8], 16) << 24) | (int(s[4:6], 16) << 16) | (int(s[2:4], 16) << 8) | int(s[0:2], 16)

def ulonglong2mac(u):
    return '%02x-%02x-%02x-%02x-%02x-%02x' % (u & 0xFF, (u >> 8) & 0xFF, (u >> 16) & 0xFF, (u >> 24) & 0xFF, (u >> 32) & 0xFF, (u >> 40) & 0xFF)

def get_config(db, k, dv=0):
    cur = db.cur()
    cur.execute('select cval from config where cid = %d limit 1' % (k,))
    rs = cur.fetchall()
    if rs:
        return int(rs[0][0])
    else:
        return dv
    
def set_config(db, k, v):
    cur = db.cur()
    if v == None:
        cur.execute('delete from config where cid = %d limit 1' % (k,))
    else:
        cur.execute('insert into config values(%d,%d) on duplicate key update cval=%d' % (k,v,v))

def get_configv2(db, k, dv=''):
    cur = db.cur()
    cur.execute("select cval from configv2 where ckey=%s limit 1", (k,))
    rs = cur.fetchall()
    if rs:
        return rs[0][0]
    else:
        return dv

def set_configv2(db, k, v):
    cur = db.cur()
    if v == None:
        cur.execute("delete from configv2 where ckey=%s limit 1", (k,))
    else:
        cur.execute("insert into configv2 values(%s,%s) on duplicate key update cval=%s", (
            k, v, v
        ))

def round_ex(f, p=2, e=0.0000001):
    if f >= 0:
        return round(f + e, p)
    else:
        return round(f - e, p)
    


#backward compatible
def get_config_(db, k, dv=0):
    db.query('select cval from config where cid = %d limit 1' % (k,))
    rs = db.use_result().fetch_row()
    return rs and int(rs[0][0]) or dv
    
def set_config_(db, k, v):
    if v == None:
        db.query('delete from config where cid = %d limit 1' % (k,))
    else:
        db.query('insert into config values(%d,%d) on duplicate key update cval=%d' % (k,v,v))


def get_configv2_(db, k, dv=''):
    if isinstance(k, unicode): k = k.encode('utf8')
    db.query("select cval from configv2 where ckey='%s' limit 1" % (db.escape_string(k),))
    rs = db.use_result().fetch_row()
    return rs and rs[0][0] or dv

def set_configv2_(db, k, v):
    if isinstance(k, unicode): k = k.encode('utf8')
    if v == None:
        db.query("delete from configv2 where ckey='%s' limit 1" % (db.escape_string(k),))
    else:
        if isinstance(v, unicode): v = v.encode('utf8')
        ve = db.escape_string(v)
        db.query("insert into configv2 values('%s','%s') on duplicate key update cval='%s'" % (
            db.escape_string(k), ve, ve
        ))


