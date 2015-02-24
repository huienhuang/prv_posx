from sync_helper import *
import sys
import json
import time
import data_helper
import cPickle

SNAPSHOT_CFNS = [u'Type', u'Title', u'FName', u'LName', u'Company', u'Address1', u'Address2', u'City', u'State', u'ZIP', u'Country', u'ShipAddrName', u'ShipCompany', u'ShipFullName', u'ShipAddress', u'ShipAddress2', u'ShipCity', u'ShipState', u'ShipZIP', u'ShipCountry', u'Phone1', u'Phone2', u'Phone3', u'Phone4', u'Email', u'Comments', u'UDF1', u'UDF2', u'UDF3', u'UDF4', u'UDF5', u'UDF6', u'UDF7', u'TaxArea', u'PriceLevel', u'DiscType', u'TrackRewards', u'CustomerID', u'WebNumber', u'WebFullNumber', u'EmailNotify', u'AR', u'UseAccCharge', u'AcceptChecks', u'DefaultShipTo', u'NoShipToBill', u'CreditLimit', u'DiscAllowed']

CFNS_FLOAT = "disctype,creditused".split(',')
CFNS_STR = "discallowed,type,lname,company,address1,address2,city,state,zip,country,phone1,phone2,phone3,phone4,email,udf1,udf2,udf3,udf5,taxarea,customerid".split(',')

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


def create_snapshots(mdb, lrs, mode):
    if mode:
        reps = lrs
        while reps:
            qjs = []
            for r in reps[:1000]: qjs.append( "(%d,%d,'%s')" % (r[0], r[1], mdb.escape_string(cPickle.dumps(r[2], 1))) )
            mdb.query("insert into sync_customer_snapshots values " + ','.join(qjs))
            reps = reps[1000:]
        return

    mdb.query('select * from sync_customer_snapshots where sid in (%s)' % ( ','.join([str(f_x[0]) for f_x in lrs]) ))
    res = mdb.store_result()
    rs = {}
    for r in res.fetch_row(maxrows=0): rs[ r[0] ] = cPickle.loads(r[2])

    reps = []
    difs = []
    for sid,lts,n in lrs:
        o = rs.get(sid)
        if o == None:
            reps.append( (sid, lts, n) )
            continue
        else:
            dif = []
            for i in range(len(SNAPSHOT_CFNS)):
                if o[i] != n[i]: dif.append( (i, n[i]) )
            if dif:
                reps.append( (sid, lts, n) )
                difs.append( (sid, lts, dif) )

    reps_len = len(reps)
    difs_len = len(difs)

    while reps:
        qjs = []
        for r in reps[:1000]: qjs.append( "(%d,%d,'%s')" % (r[0], r[1], mdb.escape_string(cPickle.dumps(r[2], 1))) )
        mdb.query("replace into sync_customer_snapshots values " + ','.join(qjs))
        reps = reps[1000:]

    while difs:
        qjs = []
        for r in difs[:1000]: qjs.append( "(null,%d,%d,'%s')" % (r[0], r[1], mdb.escape_string(cPickle.dumps(r[2], 1))) )
        mdb.query("replace into sync_customer_chg values " + ','.join(qjs))
        difs = difs[1000:]


    if reps_len or difs_len: print 'CHG: S(%d), C(%d)' % (reps_len, difs_len)


def sync_customers(cj_data, mode=0):
    cur,sur = pos_db()
    mdb = sys_db()
    
    lrs = []
    feed = []
    
    if mode:
        mdb.query('delete from sync_customers')
        mdb.query('delete from sync_customer_snapshots')
        mdb.query('delete from sync_customer_chg')
        where_sql = 'datastate=0'
    else:
        sids = [ str(x[1]) for x in cj_data if x[0] and x[0].lower() == 'customer' ]
        if not sids: return 0
        where_sql = 'sid in (%s)' % (','.join(sids),)

    rep_seq = del_seq = 0
    sql = ''
    cur.execute("select * from customer where " + where_sql)
    cur_nzs = [ d[0].lower() for d in cur.description ]
    for r in cur.rows():
        r = dict(zip(cur_nzs, r))

        if r['datastate']:
            del_seq += 1
            mdb.query("delete from sync_customers where sid=%d limit 1" % (r['sid'],))
            feed.append( (r['sid'], 1) )
            continue

        lr = []
        for f_k in SNAPSHOT_CFNS: lr.append(r[f_k.lower()])
        
        for f_k in CFNS_FLOAT: r[f_k] = rf2(r[f_k])
        for f_k in CFNS_STR: r[f_k] = r[f_k] or ''
        
        sid = r['sid']
        del r['sid']
        feed.append( (sid, 0) )

        lts = int(time.mktime(time.strptime(r['lastedit'].split('.')[0], '%Y-%m-%d %H:%M:%S')))
        lrs.append( (sid, lts, lr) )
        
        #generate location hash
        r['loc'] = data_helper.get_location_hash(r['address1'], r['city'], r['state'], r['zip'])
        
        lookup = set()
        if r['address1']: lookup.add(r['address1'].strip().lower())
        if r['phone1']: lookup.add( data_helper.parse_phone_num(r['phone1']) )
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
    
    if lrs: create_snapshots(mdb, lrs, mode)

    while feed:
        qjs = mdb.escape_string( json.dumps(feed[:1000], separators=(',',':')) )
        #mdb.query("insert into sync_feed values (null,1,'%s')" % (
        #    qjs,
        #    )
        #)
        mdb.query("insert into sync_chg values (null,1,'%s')" % (
            qjs,
            )
        )
        feed = feed[1000:]
    
    print 'sync_customers: R(%d), D(%d)' % (rep_seq, del_seq)
    return rep_seq + del_seq


g_sync_cb = ('customers', sync_customers)

if __name__ == '__main__':
    sync_main(g_sync_cb)
    #sync_customers(None, 1)
