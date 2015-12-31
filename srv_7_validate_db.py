import config
import db
import re
import thread
import time
import db

print 'checking missing invoice...'

def get_receipt_total(r):
    sid,refsid,rnum,rtype,rstatus,clerk,ttype,qbstatus,subtotal,disc_percent,items_count = r[:11]
    
    sur.execute('select sum(TenderAmount) from ReceiptTender where SID = ? and TenderType = 6 group by TenderType', (sid,))
    rc = sur.fetchone()
    if rc:
        acct_amt = float(rc[0])
    else:
        acct_amt = 0.0
    
    sur.execute('select Clerk,sum(Price*Qty),sum(PriceTax*Qty) from ReceiptItem where SID = ? and ItemSID != 1000000005 group by clerk', (sid,))
    disc = (100 - float(disc_percent)) / 100
    item_total_tax = 0.0
    clerk_total = []
    for s in sur.rows():
        s_clerk,price,price_tax = s
        
        price = float(price) * disc
        price_tax = float(price_tax) * disc
        if rtype > 0:
            price = -price
            price_tax = -price_tax
        
        price = round(price, 5)
        p_acct = p_other = 0.0
        if acct_amt:
            p_acct = price
        else:
            p_other = price
        
        item_total_tax += price_tax
        clerk_total.append( [s_clerk, price, p_acct, p_other] )
    
    qb_stype = False
    if qbstatus:
        sur.execute('select count(*) from FinancialDetail where POS_SID = ?', (sid,))
        qbcount = int(sur.fetchone()[0])
        if not qbcount:
            if item_total_tax == 0.0 or items_count == 0 or rtype == 1 and rstatus == 2 or rtype == 0 and rstatus == 1:
                qb_stype = True
            else:
                print ">>>Error: No QB Transaction", r
    
    return (bool(qbstatus), round(item_total_tax, 2) > 0 and acct_amt and not qb_stype, clerk_total)


db_qb = db.db_qb()
cur_qb = db_qb.cursor()
sur_qb = db_qb.cursor()

qb_invoices = {}
regx_posnum = re.compile(r'pos receipt[\s]*#[\s]*([0-9]+)', re.S|re.I|re.M)
cur_qb.execute("select transaction_id,memo,transaction_date,doc_num from abmc_invoice_header")
for r in cur_qb.rows():
    tid,memo,tdate,docnum = r
    if not memo: continue
    m = regx_posnum.search(memo)
    if not m: continue
    rnum = int(m.group(1))
    
    if qb_invoices.has_key(rnum): print '>qb dup', r, qb_invoices[rnum]
    
    qb_invoices[rnum] = r

print 'count:', len(qb_invoices)

db_pos = db.db_pos()
cur = db_pos.cursor()
sur = db_pos.cursor()

cur.execute("select SID,ReceiptRefSID,ReceiptNum,ReceiptType,ReceiptStatus,Clerk,TenderType,QBFSStatus,(SubTotal-DiscAmount),DiscPercent,ItemsCount,ReceiptDate,(select top 1 company from customer c where c.sid=r.billtosid order by c.sid asc) as company"
            + " from Receipt r where datastate = 0 and ReceiptType < 2 order by receiptnum asc")
for r in cur.rows():
    rtotal = get_receipt_total(r)
    if not rtotal: continue
    is_qb_transfered,is_invoice,clerk_total = rtotal
    
    if not is_qb_transfered or not is_invoice: continue
    if not qb_invoices.has_key(r[2]):
        print 'ENF:', r[2], r


