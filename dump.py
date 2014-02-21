import db as mydb
import json
import csv


items_no = """
11140
13190
11144
11138
12264
12043
11093
12014
12273
88036
11097
11147
11019
11139
11145
11011
11094
11076
12015
13192
11137
12041
12027
12016
12026
13031
12044
13028
12381
11004
11077
88151
13114
11112
55005
11021
11003
88031
13191
11007
13036
13115
13063
11013
12030
11099
13187
12251
13035
88066
13032
12382
13109
13113
12048
11100
11101
12032
88033
55014
11005
55001
11001
11002
12391
11146
11023
88038
"""

mdb = mydb.db_mdb()
cur = mdb.cursor()

items_no = [f_x.strip() for f_x in items_no.strip().split('\n') if f_x.strip()]

wt = csv.writer( open("qty.csv", 'wb') )

for num in items_no:
    cur.execute('select detail from sync_items where num=%s', (num, ))
    jsd = json.loads(cur.fetchall()[0][0])

    units = jsd['units']
    l_units = []
    for unit in units:
        if not unit[1]: continue
        l_units.append( '%s:%s' % (unit[2].upper(), (unit[1] or '').lower()) )
    s_units = ','.join(l_units)

    wt.writerow( [num, s_units.encode('utf8')] )


