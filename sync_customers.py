from sync_helper import *
import sys
import json
import time
import phonenum_parser


QB_VFS = (
    ('state', None, True),
    ('lname', 25, None),
    ('company', 41, None),
    ('phone1', 21, None),
)
def check_inconsistency(r):
    incon = []
    for name,max_len,force_case in QB_VFS:
        d = r[name] or ''
        if max_len != None and len(d) > max_len: incon.append('%s: max len(%d)' % (name, max_len))
        if force_case != None and (force_case and d.upper() or d.lower()) != d:
            incon.append('%s: %s only' % (name, force_case and 'upper' or 'lower'))
    if incon: r['incon'] = incon
    
    return len(incon)

def sync_customers(cj_data, mode=0):
    cur,sur = pos_db()
    mdb = sys_db()
    
    feed = []
    
    if mode:
        mdb.query('delete from sync_customers')
        where_sql = 'datastate=0'
    else:
        sids = [ str(x[1]) for x in cj_data if x[0] and x[0].lower() == 'customer' ]
        if not sids: return 0
        where_sql = 'sid in (%s)' % (','.join(sids),)

    rep_seq = del_seq = 0
    sql = ''
    cur.execute("select sid,datastate,pricelevel,disctype,creditused,discallowed,type,lname,company,address1,address2,city,state,zip,country,phone1,phone2,phone3,phone4,email,udf1,udf2,udf3,udf5,taxarea,customerid from customer where " + where_sql)
    cur_nzs = [ d[0].lower() for d in cur.description ]
    for r in cur.rows():
        r = list(r[:3]) + map(rf2, r[3:5]) + [ x or '' for x in r[5:] ]
        r = dict(zip(cur_nzs, r))
        
        if r['datastate']:
            del_seq += 1
            mdb.query("delete from sync_customers where sid=%d limit 1" % (r['sid'],))
            feed.append( (r['sid'], 1) )
            continue
        
        sid = r['sid']
        del r['sid']
        feed.append( (sid, 0) )
        
        lookup = set()
        if r['address1']: lookup.add(r['address1'].strip().lower())
        if r['phone1']: lookup.add( phonenum_parser.parse_phone_num(r['phone1']) )
        lookup.discard(u'')
        
        flag = 0
        if check_inconsistency(r): flag |= 1
        
        zipcode = r['zip'].split('-')[0].strip()[:5]
        if zipcode and zipcode.isdigit() and len(zipcode) <= 5:
            zipcode = int(zipcode)
        else:
            zipcode = 0
        
        rep_seq += 1
        sqlt = "(%d,'%s','%s','%s',%d,%d)," % (
            sid,
            mdb.escape_string( (r['company'] or r['lname'] or u'').encode('utf8') ),
            mdb.escape_string( u' '.join(lookup).encode('utf8') ),
            mdb.escape_string( json.dumps(r, separators=(',',':')) ),
            zipcode,
            flag
        )
        
        if len(sql) + len(sqlt) >= 1024 * (1024 - 1):
            sql = 'replace into sync_customers values ' + sql[:-1]
            mdb.query(sql)
            sql = ''
        sql += sqlt
    
    if sql:
        sql = 'replace into sync_customers values ' + sql[:-1]
        mdb.query(sql)
        sql = ''
    
    while feed:
        mdb.query("insert into sync_feed values (null,1,'%s')" % (
            mdb.escape_string( json.dumps(feed[:1000], separators=(',',':')) ),
            )
        )
        feed = feed[1000:]
    
    #if rep_seq or del_seq:
    #    if mode:
    #        mdb.query('optimize table sync_customers')
    #        mdb.use_result()
    
    print 'sync_customers: R(%d), D(%d)' % (rep_seq, del_seq)
    return rep_seq + del_seq


g_sync_cb = ('customers', sync_customers)

if __name__ == '__main__':
    sync_main(g_sync_cb)
    #sync_customers(None, 1)
    #sync_customers( (('customer', -7777123806535057151), ('customer', -7777123797550857983), ('customer', -7777123806493114111)) )
