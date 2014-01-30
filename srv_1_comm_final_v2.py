import sqlanydb
import csv
import sys
import re
import os
import json
import db as mydb
import datetime
import cgi


def errprint(fmt, *arg):
    s = fmt % arg
    print s
    lerr_fp.write(s)

#from_date = sys.argv[1]
#to_date = sys.argv[2]
if len(sys.argv) == 2:
    dt = datetime.date(int(sys.argv[1][:4]), int(sys.argv[1][4:6]), int(sys.argv[1][6:8]))
else:
    dt = datetime.date.today()

year = dt.year
month = dt.month

to_date = "%04d-%02d-01" % (year, month)
month -= 1
if month < 1:
    month = 12
    year -= 1
from_date = "%04d-%02d-01" % (year, month)
inv_date = year * 100 + month

data_file = os.path.join(os.getcwd(), 'data', from_date + '_cr.txt')
lerr_file = os.path.join(os.getcwd(), 'data', from_date + '_er.txt')

print "start comm %s %s" % (from_date, to_date)

if os.path.exists(data_file):
    print "data file exists"
    sys.exit()
    
if datetime.date.today().day <= 1:
    print "day 1 - exit"
    sys.exit()


db_sys = mydb.db_default()
db_pos = mydb.db_pos()
db_qb = mydb.db_qb()


lerr_fp = open(lerr_file, "a")

def get_inv_paid_hist(rnum):
    db_sys.query('select inv_date,inv_qbnum,inv_qbdate from invoice where inv_num=%d and inv_date!=%d and inv_flag=1' % (rnum, inv_date))
    return db_sys.use_result().fetch_row(maxrows=0)

def get_receipt_total(r):
    sid,refsid,rnum,rtype,rstatus,clerk,ttype,qbstatus,subtotal,disc_percent,items_count = r[:11]
    
    #print "#", rnum
    if qbstatus != 1:
        if qbstatus != 0: errprint('>>Error Status: %s', r)
        return None
    
    sur.execute('select count(*) from FinancialDetail where POS_SID = ?', (sid,))
    qbcount = int(sur.fetchone()[0])
    if not qbcount: #reversed
        if not( items_count == 0 or rtype == 1 and rstatus == 2 or rtype == 0 and rstatus == 1 ):
            errprint(">>>Error: Not Reversed %s", r)
        return None
    
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
    
    return (round(item_total_tax, 2) > 0 and acct_amt, clerk_total)


g_clerk = {}
g_receipt = {}

cur = db_pos.cursor()
sur = db_pos.cursor()

cur.execute("select SID,ReceiptRefSID,ReceiptNum,ReceiptType,ReceiptStatus,Clerk,TenderType,QBFSStatus,(SubTotal-DiscAmount),DiscPercent,ItemsCount,ReceiptDate,(select top 1 company from customer c where c.sid=r.billtosid order by c.sid asc) as company"
            + " from Receipt r where datastate = 0 and ReceiptType < 2 and ReceiptDate >= ? and ReceiptDate < ? order by receiptnum asc", (from_date, to_date))

for r in cur.rows():
    rtotal = get_receipt_total(r)
    if not rtotal: continue
    is_invoice,clerk_total = rtotal
    rnum = r[2]
    rtype = r[3]
    clerk = r[5]

    g_receipt[rnum] = [ clerk, int(not is_invoice), None, None, r[8], r[11], r[12] and cgi.escape(r[12]) or '' ]
    
    for v in clerk_total:
        i_clerk = v[0]
        i_total,i_account,i_other = v[1:]
        #0:total,1:other_total,2:acct_total,3:acct_recv_pending,4:acct_ret_pending,5:acct_recv,6:acct_ret,7:acct_recv_prev,8:acct_ret_prev
        cd = g_clerk.setdefault(i_clerk, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, {}, {}])
        cd[0] += i_total
        cd[1] += i_other
        cd[2] += i_account
        
        if is_invoice:
            idx = 3
        else:
            idx = 5
        
        if i_account > 0:
            cd[idx + 0] += i_account
        else:
            cd[idx + 1] += i_account
        
        cd[9][rnum] = [i_total, i_account]
    

print "-- start qb lookup --"

cur_qb = db_qb.cursor()
sur_qb = db_qb.cursor()

regx_posnum = re.compile('pos receipt #([0-9]+)', re.S|re.I|re.M)
cur_qb.execute("select transaction_id,memo,transaction_date,doc_num from abmc_invoice_header where is_paid_bool = 1 and transaction_id in"
               + " (select transaction_id from abmc_transaction_link where link_type in (3,4) and is_t1_source_bool = 0 group by transaction_id having max(transaction_date) >= ? and max(transaction_date) < ?)",
               (from_date, to_date)
               )
for r in cur_qb.rows():
    tid,memo,tdate,docnum = r
    if not memo: continue
    m = regx_posnum.search(memo)
    if not m: continue
    rnum = int(m.group(1))
    
    inv_paid_hist = get_inv_paid_hist(rnum)
    if inv_paid_hist:
        errprint(">>Err:Invoice Paid Already!, %s %s", rnum, inv_paid_hist)
        continue
    
    cur.execute("select SID,ReceiptRefSID,ReceiptNum,ReceiptType,ReceiptStatus,Clerk,TenderType,QBFSStatus,(SubTotal-DiscAmount),DiscPercent,ItemsCount,ReceiptDate,(select top 1 company from customer c where c.sid=r.billtosid order by c.sid asc) as company from Receipt r where datastate = 0 and ReceiptNum = ?", (rnum,))
    rr = cur.fetchone()
    if not rr:
        errprint(">>Err:No Such Receipt No - %s %s", rnum, r)
        continue
    
    if rr[3] >= 2: continue
    
    rtotal = get_receipt_total(rr)
    if not rtotal:
        errprint(">>Err:Receipt - %s %s", rnum, rr)
        continue
    
    is_invoice,clerk_total = rtotal
    if not is_invoice: continue
    clerk = rr[5]
    
    rpt = g_receipt.get(rnum, None)
    if rpt:
        if rpt[1]:
            errprint(">>Err:Invoice Not Receivable, %s %s", rnum, rr)
            continue
        else:
            rpt[1] = 1
            rpt[2] = tdate
            rpt[3] = docnum
    else:
        g_receipt[rnum] = [ clerk, 1, tdate, docnum, rr[8], rr[11], rr[12] and cgi.escape(rr[12]) or '' ]
    
    for v in clerk_total:
        i_clerk = v[0]
        i_total,i_account,i_other = v[1:]
        
        cd = g_clerk.setdefault(i_clerk, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, {}, {}])
        if rpt:
            if i_account > 0:
                cd[3] -= i_account
                cd[5] += i_account
            else:
                cd[4] -= i_account
                cd[6] += i_account
        else:
            if i_account > 0:
                cd[7] += i_account
            else:
                cd[8] += i_account
            
            cd[10][rnum] = [i_total, i_account]
    
    
print ">start exporting<"

json.dump([g_clerk, g_receipt], open(data_file, 'wb'))

print "looking for duplicated invoices ..."

db = db_sys
db.query('delete from invoice where inv_date = %d' % (inv_date,))
for k, v in g_receipt.items():
    qs = 'select inv_date,inv_qbnum,inv_qbdate from invoice where inv_num = %d and inv_date != %d'% (k, inv_date)
    if v[1]: qs += ' and inv_flag = 1'
    db.query(qs)
    r = db.use_result().fetch_row(maxrows=0)
    if r: errprint("dup %s %s %s", k, v, r)
    
print "inserting data"
s = ''
for k, v in g_receipt.items():
    s += "(%d,%d,'%s',%d,'%s','%s','%s')," % (k, inv_date, v[0], v[1], v[2] or '', v[3] or '', v[4])
if s: db.query("insert into invoice values " + s[:-1])

print len(g_receipt), db.affected_rows()

db.close()
print ">>Done<<"

