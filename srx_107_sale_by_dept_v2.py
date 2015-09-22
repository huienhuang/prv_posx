import config
import datetime
import time
import cPickle
import json
import os
import db as mydb
import const


USER_MAP = {
    'sales1': 'ray',
    'sales2': 'anthony',
    'sales3': 'joe',
    'sales8': 'nicole',
    'sales5': 'jimmy',
    'sales6': 'sally',
}
REP_ROLE_BITMAP = (1 << config.BASE_ROLES_MAP['Sales']) | (1 << config.BASE_ROLES_MAP['Delivery'])


mdb = mydb.db_mdb()
cur = mdb.cursor()

cur.execute("select user_name,user_roles from user")
ROLES = dict((v[0].lower(), v[1]) for v in cur.fetchall())

cur.execute("select cval from configv2 where ckey='departments' limit 1")
DEPTS = {}
for x in cPickle.loads( cur.fetchall()[0][0] ):
    cate = const.ITEM_D_DEPT.get(x[0].lower())
    DEPTS[x[1]] = (x[1], x[0], cate)

ITEM_DEPTS = {}
cur.execute('select sid,deptsid from sync_items')
for r in cur.fetchall(): ITEM_DEPTS[r[0]] = DEPTS.get(r[1])

ITEM_NUMS = {}
cur.execute('select sid,num from sync_receipts_items')
for r in cur.fetchall(): ITEM_NUMS[r[0]] = r[1]

g_clerks = {}
g_items = {}
cur.execute('select * from sync_receipts where sid_type=0 and (type&0xFF00)<0x0200 order by sid asc')
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    
    items = json.loads(r['items_js'])
    gjs = json.loads(r['global_js'])
    
    rtype = (r['type'] >> 8) & 0xFF
    
    disc = 1
    if gjs['subtotal']: disc = 1 - gjs['discamt'] / gjs['subtotal']
    
    tp = time.localtime(r['order_date'])
    dt_i = tp.tm_year * 100 + tp.tm_mon

    for t in items:
        if t['itemsid'] == 1000000005 or not t['qty']: continue
        ttl_base_qty = t['nunits'] * t['qty']
        ttl_price = t['price'] * t['qty'] * disc
        ttl_cost = t['cost'] * t['qty']
        
        if rtype > 0:
            ttl_base_qty = -ttl_base_qty
            ttl_price = -ttl_price
            ttl_cost = -ttl_cost
    
        nt = g_items.setdefault(t['itemsid'], [None, {}])
        st = nt[1].setdefault(dt_i, [0, 0, 0, 0])
        nt[0] = t['deptsid']

        st[0] += ttl_base_qty
        st[1] += ttl_price
        st[2] += ttl_cost
        st[3] += 1

        clerk = (t['clerk'] or '').lower()
        clerk = USER_MAP.get(clerk, clerk)
        if not (ROLES.get(clerk, 0) & REP_ROLE_BITMAP): clerk = ''
        cd = g_clerks.setdefault(clerk, [{}])[0].setdefault(dt_i, [0, 0, 0])
        cd[1] += ttl_price
        cd[2] += ttl_cost



cur.execute('select *,(select user_name from user u where u.user_id=s.ord_assoc_id limit 1) as user_name from sorder s where (ord_flag&8)!=0')
nzs = cur.column_names
for r in cur:
    r = dict(zip(nzs, r))
    
    items = json.loads(r['ord_items_js'])
    gjs = json.loads(r['ord_global_js'])
    
    rtype = r['ord_flag'] & (1 << 1)
    disc = (100 - gjs['disc']) / 100
    
    tp = time.localtime(r['ord_order_date'])
    dt_i = tp.tm_year * 100 + tp.tm_mon

    clerk = (r['user_name'] or '').lower()
    clerk = USER_MAP.get(clerk, clerk)
    if not (ROLES.get(clerk, 0) & REP_ROLE_BITMAP): clerk = ''
    cd = g_clerks.setdefault(clerk, [{}])[0].setdefault(dt_i, [0, 0, 0])

    for t in items:
        ttl_base_qty = t['in_base_qty']
        ttl_price =  t['in_price'] * t['in_qty'] * disc
        ttl_cost = t['prev_qty'][4] * ttl_base_qty
        
        if rtype > 0:
            ttl_base_qty = -ttl_base_qty
            ttl_price = -ttl_price
            ttl_cost = -ttl_cost
            
        nt = g_items.setdefault(t['id'], [None, {}])
        st = nt[1].setdefault(dt_i, [0, 0, 0, 0])

        st[0] += ttl_base_qty
        st[1] += ttl_price
        st[2] += ttl_cost
        st[3] += 1

        cd[1] += ttl_price
        cd[2] += ttl_cost


g_depts = {}
for sid,td in g_items.items():
    td[0] = dept = ITEM_DEPTS.get(sid, DEPTS.get(td[0])) or (None, None, None)
    dd = g_depts.setdefault(dept[0], [dept, {}, set()])
    dd[2].add(sid)

    n_l_ts = []
    d_ds = dd[1]
    for f_k,f_v in td[1].items():
        n_l_ts.append( (f_k,map(lambda f_x: round(f_x, 2), f_v[:-1]) + f_v[-1:]) )
        ds = d_ds.setdefault(f_k, [0, 0, 0, 0])
        for i in range(len(ds)): ds[i] += f_v[i]

    n_l_ts.sort(key=lambda f_x: f_x[0])
    td[1] = n_l_ts

g_cates = {}
for sid,dd in g_depts.items():
    dd[2] = sorted(list(dd[2]), key=lambda f_x: ITEM_NUMS.get(f_x, 0))
    
    n_l_ds = []
    d_cs = g_cates.setdefault(dd[0][2], [{}])[0]
    for f_k,f_v in dd[1].items():
        n_l_ds.append( (f_k,map(lambda f_x: round(f_x, 2), f_v[:-1]) + f_v[-1:]) )
        cs = d_cs.setdefault(f_k, [0, 0, 0, 0])
        for i in range(len(cs)): cs[i] += f_v[i]

    n_l_ds.sort(key=lambda f_x: f_x[0])
    dd[1] = n_l_ds


g_types = {}
for cnz,cd in g_cates.items():
    n_l_ds = []
    d_cs = g_types.setdefault(const.ITEM_D_CATE2.get(cnz) or "", [{}])[0]
    for f_k,f_v in cd[0].items():
        n_l_ds.append( (f_k,map(lambda f_x: round(f_x, 2), f_v[:-1]) + f_v[-1:]) )
        cs = d_cs.setdefault(f_k, [0, 0, 0, 0])
        for i in range(len(cs)): cs[i] += f_v[i]

    n_l_ds.sort(key=lambda f_x: f_x[0])
    cd[0] = n_l_ds


for cnz,cd in g_types.items():
    cd[0] = [ (f_k,map(lambda f_x: round(f_x, 2), f_v[:-1]) + f_v[-1:]) for f_k,f_v in cd[0].items() ]
    cd[0].sort(key=lambda f_x: f_x[0])


for cnz,cd in g_clerks.items():
    cd[0] = [ (f_k,map(lambda f_x: round(f_x, 2), f_v)) for f_k,f_v in cd[0].items() ]
    cd[0].sort(key=lambda f_x: f_x[0])


fnz = os.path.join(config.DATA_DIR, 'items_stat_v2.txt')
cPickle.dump({'cates': g_cates, 'depts': g_depts, 'types': g_types, 'items': g_items, 'clerks': g_clerks}, open(fnz, 'wb'), 1)
print "Done"
