import config
import db as mydb
import datetime
import time
import json
import cPickle
import os

mdb = mydb.db_mdb()
cur = mdb.cursor()


print "delivery receipt"
g_d_records = {}
cur.execute("select d_id,ts from deliveryv2")
for r in cur.fetchall():
    dt = time.localtime(r[1])
    g_d_records[ r[0] ] = ( int(time.mktime(datetime.date(dt.tm_year, dt.tm_mon, 1).timetuple())), r[1] )

g_d_mons = {}
g_d_receipts = {}
cur.execute("select d_id,num,driver_id,delivered,problem_flag,problem_flag_s from deliveryv2_receipt where d_excluded=0 order by d_id asc")
nzs = cur.column_names
for r in cur.fetchall():
    r = dict(zip(nzs, r))
    
    date = g_d_records[ r['d_id'] ]
    if date == None: continue
    r['date'] = date[1]
    
    rr = g_d_receipts.get(r['num'])
    if rr == None:
        g_d_mons.setdefault(date[0], {'nums': [], 'perfect': 0, 'completed': 0, 'qtys': 0, 'lines': 0})['nums'].append(r['num'])
        rr = g_d_receipts[ r['num'] ] = []
    rr.append( r )


g_receipts = {}
cur.execute('select num,items_js from sync_receipts where num in (%s)' % ','.join(map(str, g_d_receipts.keys())) )
for r in cur.fetchall(): g_receipts[ r[0] ] = json.loads(r[1])

for mon,m_data in g_d_mons.items():
    for num in m_data['nums']:
        rr = g_d_receipts[num]
        
        d_deli = 1
        d_p_flag = 0
        d_p_flag_s = 0
        for r in rr:
            d_deli &= r['delivered']
            d_p_flag |= r['problem_flag']
            d_p_flag_s |= r['problem_flag_s']
    
        if d_deli:
            if not d_p_flag: m_data['completed'] += 1
            if not d_p_flag_s: m_data['perfect'] += 1

        lines = qtys = 0
        for item in g_receipts[num]:
            if item['itemsid'] == 1000000005: continue
            if item['qty'] <= 0: continue
                
            lines += 1
            qtys += item['qty']
        
        m_data['lines'] += lines
        m_data['qtys'] += qtys
        
    
    
def get_mon_ds(ts=None):
    tp = time.localtime(ts)
    start_ts = int(time.mktime(datetime.date(tp.tm_year, tp.tm_mon, 1).timetuple()))
    
    next_mon = tp.tm_mon + 1
    next_yr = tp.tm_year
    if next_mon > 12:
        next_mon = 1
        next_yr += 1
    end_ts = int(time.mktime(datetime.date(next_yr, next_mon, 1).timetuple()))
    
    return ( start_ts, end_ts )


PERM_WAREHOUSE = 1 << config.USER_PERM_BIT['warehouse']
g_users = {}
cur.execute('select user_id,user_lvl,in_ts,out_ts from clockin_hist where flag&2=0 order by in_ts asc')
for r in cur.fetchall():
    user_id,user_lvl,in_ts,out_ts = r
    if not (user_id & PERM_WAREHOUSE): continue
    
    days = g_users.setdefault(user_id, {})
    while(in_ts < out_ts):
        start_ts_mon, end_ts_mon = get_mon_ds(in_ts)
        stat = days.setdefault(start_ts_mon, [in_ts, 0, 0])
        
        in_ts_mon = max(in_ts, stat[1])
        out_ts_mon = min(out_ts, end_ts_mon)
        
        if in_ts_mon < out_ts_mon:
            stat[1] = out_ts_mon
            stat[2] += out_ts_mon - in_ts_mon
            
        in_ts = out_ts_mon


for mon,m_data in g_d_mons.items():
    work_secs = 0
    for user_id, days in g_users.items():
        if not days.has_key(mon): continue
        work_secs += days.get(mon)[2]
    m_data['work_secs'] = work_secs

mons = g_d_mons.items()
mons.sort(key=lambda f_x:f_x[0])
cPickle.dump({'mons': mons}, open(os.path.join(config.DATA_DIR, 'delivery_report.txt'), 'wb'), 1)



