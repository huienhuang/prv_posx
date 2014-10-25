
REC_FLAG_CHANGED = 1 << 3
REC_FLAG_PARTIAL_CHANGED = 1 << 7

def get_sc_lite(cur, sc_id):    
    cur.execute('select sc_id,sc_flag,sc_date,doc_type,doc_sid from schedule where sc_id=%s', (sc_id,))
    rows = cur.fetchall()
    if not rows: return None
    r = dict(zip(cur.column_names, rows[0]))
    
    if r['doc_type']:
        cur.execute('select sid,num,global_js from sync_receipts where sid_type=0 and sid=%s', (r['doc_sid'], ))
    else:
        cur.execute('select sid,sonum,global_js from sync_salesorders where sid=%s', (r['doc_sid'], ))  
    rows = cur.fetchall()
    if not rows: return None

    sid,num,gjs = rows[0]
    gjs = json.loads(gjs)
    r['doc'] = {'num': num, 'gjs': gjs}

    items_crc = gjs.get('items_crc')
    if r['sc_flag'] & REC_FLAG_PARTIAL and r['doc_ijs_crc'] != items_crc: r['sc_flag'] |= REC_FLAG_PARTIAL_CHANGED
            
    crc = gjs.get('crc')
    if r['sc_flag'] & REC_FLAG_ACCEPTED and r['doc_crc'] != crc: r['sc_flag'] |= REC_FLAG_CHANGED

    return r

