import mysql.connector as MySQL
import config
import winlib
import const
import boundary
import struct
import zlib
import hashlib
import base64
import json
import data_helper


dbc = MySQL.connect(**config.mysql)
cur = dbc.cursor()

cur.execute('select loc,lat,lng,js from address')
for r in list(cur.fetchall()):
    loc,lat,lng,js = r
    s = json.loads(js)['orig']
    
    n_loc = hashlib.md5(s).digest() + struct.pack('<L', zlib.crc32(s) & 0xFFFFFFFF)
    if loc[:16] != n_loc[:16]:
        print "Error"
        continue
    
    cur.execute('select count(*) from address where loc=%s', (n_loc, ))
    if cur.fetchall()[0][0]:
        print 'DUP'
        continue
    
    cur.execute('update address set loc=%s where loc=%s', (n_loc, loc))

cur.execute('select sid,detail from sync_customers')
for r in list(cur.fetchall()):
    sid,r = r
    r = json.loads(r)
    n_loc = data_helper.get_location_hash(r['address1'], r['city'], r['state'], r['zip'])
    if n_loc != r.get('loc'):
        r['loc'] = n_loc
        cur.execute('update sync_customers set detail=%s where sid=%s', (
            json.dumps(r, separators=(',',':')), sid
            )
        )

cur.execute('select sid,global_js from sync_receipts where sid_type=0')
for r in list(cur.fetchall()):
    sid,r = r
    r = json.loads(r)
    
    for n in ('customer', 'shipping'):
        cust = r.get(n)
        if not cust: continue
        chg = False
        n_loc = data_helper.get_location_hash(cust['addr1'], cust['city'], cust['state'], cust['zip'])
        if n_loc != cust.get('loc'):
            cust['loc'] = n_loc
            chg = True
    
    if chg:
        cur.execute('update sync_receipts set global_js=%s where sid=%s and sid_type=0', (
            json.dumps(r, separators=(',',':')), sid
            )
        )

cur.execute('select sid,global_js from sync_salesorders')
for r in list(cur.fetchall()):
    sid,r = r
    r = json.loads(r)
    
    for n in ('customer', 'shipping'):
        cust = r.get(n)
        if not cust: continue
        chg = False
        n_loc = data_helper.get_location_hash(cust['addr1'], cust['city'], cust['state'], cust['zip'])
        if n_loc != cust.get('loc'):
            cust['loc'] = n_loc
            chg = True
    
    if chg:
        cur.execute('update sync_salesorders set global_js=%s where sid=%s', (
            json.dumps(r, separators=(',',':')), sid
            )
        )

