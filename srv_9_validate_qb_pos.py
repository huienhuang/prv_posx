import config
import db
import re
import thread
import time
import db

db_qb = db.db_qb()
cur_qb = db_qb.cursor()

print "Check QB Customer..."
cur_qb.execute('select m.*,u.name,l.memo as memo2,l.amount_amt from abmc_invoice_header m left join abmc_customer_user u on (m.customer_id=u.customer_id) left join abmc_invoice_lineitem l on (l.target_id=m.target_id) where m.is_paid_bool!=1 and u.is_hidden_bool=1 order by u.customer_id asc')
cur_nzs = [ d[0].lower() for d in cur_qb.description ]
for r in cur_qb.rows():
    r = dict(zip(cur_nzs, r))
    print '>Inactive, %s, %s, %s, %s, %s', r['name'], r['doc_num'], r['memo'], r['amount_amt'], r['transaction_date']

regx_posnum = re.compile('pos receipt #([0-9]+)', re.S|re.I|re.M)
print "Checking QB Receipt..."
tbls = ('invoice', 'credit_memo', 'sales_receipt', 'received_payment')
data = {}
data_cid = {}
for t in tbls:
    cur_qb.execute('select m.*,u.name,l.memo as memo2,l.amount_amt from abmc_%s_header m left join abmc_customer_user u on (m.customer_id=u.customer_id) left join abmc_%s_lineitem l on (l.target_id=m.target_id) where m.memo is not null or l.memo is not null order by m.transaction_id asc' % (t,t))
    cur_nzs = [ d[0].lower() for d in cur_qb.description ]

    for r in cur_qb.rows():
        r = dict(zip(cur_nzs, r))

        memo = r['memo'] or ''
        memo2 = r['memo2'] or ''
        if not memo and not memo2: continue
        num = regx_posnum.findall(memo)
        num2 = regx_posnum.findall(memo2)
        if not num and not num2: continue
        if len(num) != len(num2) or num[0] != num2[0]:
            print '>POSNumNotMatched, %s, %s' % (memo, memo2)
            continue
        num = num[0]
        
        j = data.setdefault(num, {})
        k = j.setdefault(t, [])
        if len(k):
            print ">Dup[%s], %s, %s, %0.2f, %s, %s" % (
                t, num, r['name'], float(r['amount_amt']), r['transaction_date'],
                [x['name'] for x in k]
            )
        k.append(r)
        
        data_cid.setdefault(num, {}).setdefault(r['customer_id'], []).append(r)

print "Checking QB Receipt - Customer ID"
for k, v in data_cid.items():
    if len(v) > 1:
        print '>DiffCustomerID, %s, %s' % (k, [x[0]['name'] for x in v.values()])

db_pos = db.db_pos()
cur_pos = db_pos.cursor()
sur_pos = db_pos.cursor()

print 'Checking POS Receipt...'
cur_pos.execute("select * from Receipt r where datastate = 0 and qbfsstatus=1 order by sid asc")
cur_nzs = [ d[0].lower() for d in cur_pos.description ]
receipts = {}
for r in cur_pos.rows():
    r = dict(zip(cur_nzs, r))
    receipts[ r['sid'] ] = r

pair_receipts = []
for sid,r in receipts.items():
    sur_pos.execute('select count(*) from ReceiptItem where sid=? and ItemSID = 1000000005', (sid,))
    returned_to_account = int(sur_pos.fetchone()[0])
    
    sur_pos.execute('select count(*) from FinancialDetail where POS_SID=?', (sid,))
    fs_count = int(sur_pos.fetchone()[0])
    
    rtype = r['receipttype']
    rstatus = r['receiptstatus']
    
    skipped = False
    if not fs_count:
        if not returned_to_account and float(r['total']) == 0 and rtype < 2:
            skipped = True
        elif rstatus not in (1, 2):
            print ">NoQBTransaction: %s, %s, %s" % (r['receiptnum'], r['receiptdate'], r['creationdate'])
        
    qb = data.get( str(r['receiptnum']) )
    if qb == None and not skipped:
        if rstatus in (1, 2):
            ref_r = receipts.get(r['receiptrefsid'])
            if ref_r == None:
                print '>NotInQB,NoRefInPOS: %s, %0.2f, %s, %s' % (r['receiptnum'], float(r['total']), r['receiptdate'], r['creationdate'])
            elif data.has_key( str(ref_r['receiptnum']) ):
                print '>NotInQB,RefInQB: %s, %0.2f, %s, %s' % (r['receiptnum'], float(r['total']), r['receiptdate'], r['creationdate']) 
        else:
            print '>NotInQB: %s, %0.2f, %s, %s' % (r['receiptnum'], float(r['total']), r['receiptdate'], r['creationdate'])
    
    elif qb != None and rstatus in (1, 2):
        pair_receipts.append(r)
    
print "Checking QB Pair..."
for r in pair_receipts:
    if r.get('skipped'): continue
    
    qb_cid = data_cid.get( str(r['receiptnum']) )
    ref_r = receipts.get(r['receiptrefsid'])
    if ref_r == None: 
        print '>PairRefNotInPOS: %s' % (r['receiptnum'],)
    else:
        ref_qb_cid = data_cid.get( str(ref_r['receiptnum']) )
        if ref_qb_cid == None:
            print '>PairRefNotInQB: %s, ref#%s' % (r['receiptnum'], ref_r['receiptnum'])
        else:
            ref_r['skipped'] = True
            if len(qb_cid) != 1 or len(ref_qb_cid) != 1 or qb_cid.keys()[0] != ref_qb_cid.keys()[0]:
                print 'PairRefCustomerNotMatched, %s, %s, %s, %s' % (
                    r['receiptnum'],
                    [x[0]['name'] for x in qb_cid.values()],
                    ref_r['receiptnum'],
                    [x[0]['name'] for x in ref_qb_cid.values()]
                )


