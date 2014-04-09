import os
import glob
import sys
import config
import db as mydb
import time
import datetime


cur_dir = os.path.dirname( os.path.join(os.getcwd(), __file__) )

sa_path = r"C:\Program Files\SQL Anywhere 12\Bin32\dbsrv12.exe"
taskkill_path = r"C:\WINDOWS\system32\taskkill.exe"
cmd_path = r"C:\WINDOWS\system32\cmd.exe"
qb_restore_path = r"C:\Program Files (x86)\Intuit\QuickBooks 2009\backup_restore.exe"
zip_path = r"C:\Program Files\7-Zip\7z.exe"
pyi_path = r"C:\Python27\python.exe"

db_start_cmd= '"%s" -sb 0 -xd -x tcpip(ServerPort=%d;LO=YES) -os 1024K -o "%s" -n %s "%s"'
db_kill_cmd = '"%s" /F /IM "%s"'
db_rmdir_cmd = '"%s" /C "rmdir /S /Q "%s""'
qb_restore_cmd = '"%s" "%s" "%s"'
pos_unzip_cmd = '"%s" x "%s" -o"%s" -p"QBPOS" -y'


print "running services...."
for srv in sorted(glob.glob(os.path.join(cur_dir, 'srx_*.py'))):
    print srv
    os.spawnv(os.P_WAIT, cmd_path, ('"%s" /C ""%s" "%s" >"%s" 2>&1"' % (cmd_path, pyi_path, srv, os.path.join(cur_dir, 'log', os.path.basename(srv)+'.txt')), ) )
print ">Done<"


def qb_sort_key(n):
    ts = 0
    try:
        ds = os.path.basename(n).split('Inc ')[1].split('.')[0].strip()
        ts = int(time.mktime( time.strptime(ds, "%b %d,%Y  %I %M %p") ))
    except Exception, e:
        pass
    
    return ts

def pos_sort_key(n):
    ts = 0
    try:
        n = os.path.basename(n)
        ds = n[:8]
        ts = int(time.mktime( time.strptime(ds, "%Y%m%d") )) + int(n[8:12])
    except Exception, e:
        pass
    
    return ts


db_dst_dir = os.path.join(cur_dir, 'prv', 'db')
db_src_dir = os.path.join(cur_dir, 'shr')
db_qb_src_file = os.path.join(db_src_dir, '*.QBB')
db_pos_src_file = os.path.join(db_src_dir, '*.qpb')

qb_lst = glob.glob( db_qb_src_file )
qb_lst.sort(key=qb_sort_key, reverse=True)

pos_lst = glob.glob( db_pos_src_file )
pos_lst.sort(key=pos_sort_key, reverse=True)

if not qb_lst:
    print "no qb files"
    sys.exit()
db_qb_src_file = qb_lst[0]
db_qb_src_ts = qb_sort_key(db_qb_src_file)
for f in qb_lst[1:]:
    try:
        if(qb_sort_key(f)): os.unlink(f)
    except Exception, e:
        print e

if not pos_lst:
    print "no pos files"
    sys.exit()
db_pos_src_file = pos_lst[0]
db_pos_src_ts = pos_sort_key(db_pos_src_file)
for f in pos_lst[1:]:
    try:
        if(pos_sort_key(f)): os.unlink(f)
    except Exception, e:
        print e

print ">qb:", db_qb_src_file, db_qb_src_ts
print ">pos:", db_pos_src_file, db_pos_src_ts

dt_today = datetime.date.today()
if datetime.date.fromtimestamp(db_qb_src_ts) != dt_today:
    print "qb ts not today"
    sys.exit()
if datetime.date.fromtimestamp(db_pos_src_ts) != dt_today:
    print "pos ts not today"
    sys.exit()


db = mydb.db_default()

db.query("select cval from config where cid = %d" % (config.cid_qb_db_ts,))
r = db.use_result().fetch_row(maxrows=0)
if r and int(r[0][0]) >= db_qb_src_ts:
    print "qb: up to date"
    sys.exit()
    
db.query("select cval from config where cid = %d" % (config.cid_pos_db_ts,))
r = db.use_result().fetch_row(maxrows=0)
if r and int(r[0][0]) >= db_pos_src_ts:
    print "pos: up to date"
    sys.exit()

print ">killing database server ..."
os.spawnv(os.P_WAIT, taskkill_path, (db_kill_cmd % (taskkill_path, os.path.basename(sa_path)), ) )
print ">done"

print ">removing db dir [%s]..." % (db_dst_dir, )
os.spawnv(os.P_WAIT, cmd_path, (db_rmdir_cmd % (cmd_path, db_dst_dir), ) )
print ">done"

if not os.path.exists(db_dst_dir): os.makedirs(db_dst_dir)

db_qb_dst_file = os.path.join(db_dst_dir, os.path.basename(db_qb_src_file).replace('.QBB', '.QBW'))
db_pos_dst_file = os.path.join(db_dst_dir, "qbpos.db")

print ">extracting qb file from backup ..."
print ">>from:", db_qb_src_file
print ">>to:", db_qb_dst_file
os.spawnv(os.P_WAIT, qb_restore_path, (qb_restore_cmd % (qb_restore_path, db_qb_src_file, db_qb_dst_file), ) )
print ">done"
print "remove file"
try:
    os.unlink(db_qb_src_file)
    pass
except Exception, e:
    print e

print ">extracting pos file from backup ..."
print ">>from:", db_pos_src_file
print ">>to:", db_pos_dst_file
os.spawnv(os.P_WAIT, zip_path, (pos_unzip_cmd % (zip_path, db_pos_src_file, os.path.dirname(db_pos_dst_file)), ) )
print ">done"
print "remove file"
try:
    os.unlink(db_pos_src_file)
    pass
except Exception, e:
    print e

print ">starting databases ..."
os.spawnv(os.P_NOWAIT, sa_path, (db_start_cmd % (sa_path, 50001, os.path.join(cur_dir, 'log', 'qb.log'), 'posx_qb', db_qb_dst_file), ) )
os.spawnv(os.P_NOWAIT, sa_path, (db_start_cmd % (sa_path, 50002, os.path.join(cur_dir, 'log', 'pos.log'), 'posx_pos', db_pos_dst_file), ) )
print "done"


db.query("update config set cval = %d where cid = %d" % (db_qb_src_ts, config.cid_qb_db_ts,))
db.query("update config set cval = %d where cid = %d" % (db_pos_src_ts, config.cid_pos_db_ts,))
db.close()

print ">>>>>Done .. sleep(60sec)"
time.sleep(60)

print "running QBDEP services...."
for srv in sorted(glob.glob(os.path.join(cur_dir, 'srv_*.py'))):
    print srv
    os.spawnv(os.P_WAIT, cmd_path, ('"%s" /C ""%s" "%s" >"%s" 2>&1"' % (cmd_path, pyi_path, srv, os.path.join(cur_dir, 'log', os.path.basename(srv)+'.txt')), ) )
print ">Done<"

