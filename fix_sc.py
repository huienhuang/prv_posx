import config
import datetime
import time
import json
import db as mydb
import csv



REC_FLAG_ACCEPTED = 1 << 0
REC_FLAG_RESCHEDULED = 1 << 1
REC_FLAG_CANCELLING = 1 << 2
REC_FLAG_CHANGED = 1 << 3
REC_FLAG_DUPLICATED = 1 << 4
REC_FLAG_R_RESCHEDULED = 1 << 5
REC_FLAG_PARTIAL = 1 << 6
REC_FLAG_PARTIAL_CHANGED = 1 << 7




mdb = mydb.db_mdb()
cur = mdb.cursor()


cur.execute('select * from schedule where sc_flag&%s!=0', (
    REC_FLAG_PARTIAL,
    )
)
nzs = cur.column_names
for r in cur.fetchall():
    r = dict(zip(nzs, r))
    
    if r['doc_type']:
        cur.execute('select global_js,items_js,num from sync_receipts where sid=%s and sid_type=0 and (type&0xFF)=0', (
            r['doc_sid'],
            )
        )
    else:
        cur.execute('select global_js,items_js,sonum from sync_salesorders where sid=%s and (status>>4)=0', (
            r['doc_sid'],
            )
        )
    
    gjs,ijs,num = cur.fetchall()[0]
    gjs = json.loads(gjs)
    ijs = json.loads(ijs)
    
    if gjs.get('crc') != r['doc_crc']:
        print 'CRC Error', num, r['sc_id'], gjs.get('crc'), r['doc_crc']
        continue
    
    doc_ijs = json.loads(r['doc_ijs'])
    if doc_ijs and type(doc_ijs[0]) == dict: continue
    for i in range(len(ijs)):
        if ijs[i]['itemsid'] != doc_ijs[i][0]: raise Exception('Error')
        ijs[i]['r_qty'] = doc_ijs[i][3]
    
    
    cur.execute('update schedule set doc_ijs=%s where sc_id=%s and sc_rev=%s', (
        json.dumps(ijs, separators=(',',':')), r['sc_id'], r['sc_rev']
        )
    )
    
    
    print num, r['sc_id']








