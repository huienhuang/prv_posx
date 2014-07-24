import os
from utils import *


cid_qb_db_ts = 10001
cid_pos_db_ts = 10002
cid_user_update_seq = 1

cid__sync_last_update = 50001
cid__sync_last_cj_id = 50002
cid__sync_last_fs_id = 50003


PRICE_LEVELS = ['Regular Price', 'Wholesale 1', 'Wholesale 2', 'special', 'Dealer Price']


USER_PERM_BIT = {
'normal access': 0,
'item stat access': 1,

'time': 2,

'accounting': 3,
'accountingv2': 4,

'purchasing': 6,

'base access': 10,

'adj item qty': 11,

'cashier': 19,
'sales': 20,
'driver': 21,
'warehouse': 22,
'hr': 23,

'sales_mgr':24,
'delivery_mgr':25,

'sys': 30,
'admin': 31,
}

settings = {
'mode': 'developer',
'macs_admin': ('D4-3D-7E-B6-6E-87', '30-65-ec-3b-80-dd', '70-71-bc-03-56-e9'),
'macs_mobile': ('d8-50-e6-81-3e-dc', 'd8-50-e6-81-3d-24'),
}

if settings.has_key('macs_admin'):
    settings['macs_admin'] = set([ mac2ulonglong(f_v.replace('-', '')) for f_v in settings['macs_admin'] ])
if settings.has_key('macs_mobile'):
    settings['macs_mobile'] = set([ mac2ulonglong(f_v.replace('-', '')) for f_v in settings['macs_mobile'] ])


CFG_SEQ_MIN = 10000000
CFG_SEQ_MAX = 20000000

CFG_SCHEDULE_UPDATE_SEQ = CFG_SEQ_MIN


