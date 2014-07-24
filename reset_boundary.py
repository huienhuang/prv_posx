import mysql.connector as MySQL
import config
import winlib
import const
import boundary
import struct


def get_zone_id(lat, lng):
    idx = winlib.find_boundary(lng, lat)
    if idx < 0:
        return 0
    else:
        return ZONE_IDX_MAP[idx]
    
###
d_zones = {}
for i in range(len(const.ZONES)): d_zones[ const.ZONES[i][0] ] = i

ZONE_IDX_MAP = []
b_lst = []
for b in boundary.BOUNDARY:
    ZONE_IDX_MAP.append( d_zones[ b[0] ] )
    b_lst.append( struct.pack('%dd' % (len(b[2]), ), *b[2]) )
    
winlib.load_boundary(tuple(b_lst))
###
    

dbc = MySQL.connect(**config.mysql)
cur = dbc.cursor()

cur.execute('select loc,lat,lng from address where flag=1')
for r in list(cur.fetchall()):
    loc,lat,lng = r
    
    cur.execute('update address set zone_id=%s where loc=%s', (
        get_zone_id(lat, lng), loc
        )
    )
