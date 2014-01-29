import db as mydb
import os
import json
import re
import time
import datetime

mdb = mydb.db_default()

ct = datetime.datetime.now()
year = ct.year
month = ct.month - 2
if month <= 0:
    month += 12
    year -= 1

ts = int(time.mktime( datetime.datetime(year, month, 1).timetuple() ))
print ts

mdb.query('select count(*) from time')
print mdb.use_result().fetch_row()[0][0]

mdb.query('select count(*) from time where out_ts != 0 and out_ts < %d' % (ts, ))
print mdb.use_result().fetch_row()[0][0]

mdb.query('delete from time where out_ts != 0 and out_ts < %d' % (ts, ))

