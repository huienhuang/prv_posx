import os
import glob
import sys
import config
import db as mydb
import time
import datetime


cur_dir = config.APP_DIR

cmd_path = r"C:\WINDOWS\system32\cmd.exe"
pyi_path = r"C:\Python27\python.exe"

print "running services...."
for srv in sorted(glob.glob(os.path.join(cur_dir, 'srx_*.py'))):
    print srv
    os.spawnv(os.P_WAIT, cmd_path, ('"%s" /C ""%s" "%s" >"%s" 2>&1"' % (cmd_path, pyi_path, srv, os.path.join(cur_dir, 'log', os.path.basename(srv)+'.txt')), ) )
print ">Done<"

print "running QBDEP services...."
for srv in sorted(glob.glob(os.path.join(cur_dir, 'srv_*.py'))):
    print srv
    os.spawnv(os.P_WAIT, cmd_path, ('"%s" /C ""%s" "%s" >"%s" 2>&1"' % (cmd_path, pyi_path, srv, os.path.join(cur_dir, 'log', os.path.basename(srv)+'.txt')), ) )
print ">Done<"

