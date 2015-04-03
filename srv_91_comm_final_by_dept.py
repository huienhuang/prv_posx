import sqlanydb
import csv
import sys
import re
import os
import cPickle
import datetime
import config
import mysql.connector
import json
import const


db_mdb = mysql.connector.connect(**config.mysql)
cur_mdb = db_mdb.cursor()

db_pos = sqlanydb.connect(**config.sqlany_pos)
cur_pos = db_pos.cursor()
sur_pos = db_pos.cursor()

db_qb = sqlanydb.connect(**config.sqlany_qb)
cur_qb = db_qb.cursor()
sur_qb = db_qb.cursor()


g_errs = []
def print_err(fmt, *arg):
    s = fmt % arg
    print s
    g_errs.append(s)

def get_date_range(dt=None):
    dt = dt or datetime.date.today()
    to_year = dt.year
    to_month = dt.month
    frm_year = to_year
    frm_month = to_month - 1
    if frm_month == 0:
        frm_year -= 1
        frm_month = 12
    
    return (frm_year, frm_month, to_year, to_month)


target_dt = None#datetime.date(2014, 2, 3)
frm_year, frm_month, to_year, to_month = get_date_range(target_dt)
g_from_date_mon = frm_year * 100 + frm_month
g_from_date = '%04d-%02d-01' % (frm_year, frm_month)
g_to_date = '%04d-%02d-01' % (to_year, to_month)

print 'calc comm - %s <= receipts < %s' % (g_from_date, g_to_date)
datafile = os.path.join(config.APP_DIR, 'data', g_from_date + '_comm_clerks.txt')
datafile_a = os.path.join(config.APP_DIR, 'data', g_from_date + '_comm_receipts.txt')
if os.path.exists(datafile):
    print 'datafile exists'
    if datetime.date.today().day > 3: sys.exit()


def is_inv_exists(num, cur_date_mon):
    cur_mdb.execute('select count(*) from invoicev2 where inv_num=%s and inv_date!=%s', (num, cur_date_mon))
    return cur_mdb.fetchall()[0][0]

def parse_receipt(r):
    sur_pos.execute('select sum(TenderAmount) from ReceiptTender where SID = ? and TenderType = 6 group by TenderType', (r['sid'],))
    rc = sur_pos.fetchall()
    acct_amt = rc and float(rc[0][0]) or 0.0
    
    sur_pos.execute('select count(*) from FinancialDetail where POS_SID = ?', (r['sid'],))
    rc = sur_pos.fetchall()
    is_transfered = rc and int(rc[0][0]) or 0
    
    if r['receiptstatus'] > 0 and not is_transfered:
        is_local_reversed = True
    else:
        is_local_reversed = False
    
    r['discamount'] = float(r['discamount'])
    r['subtotal'] = float(r['subtotal'])
    
    rate = 1
    if r['subtotal']: rate = 1 - r['discamount'] / r['subtotal']
    
    items = []
    total_price_tax = 0.0
    sur_pos.execute('select i.itemsid,i.Clerk,i.Price,i.PriceTax,i.Qty,d.deptsid,i.cost from ReceiptItem i left join ReceiptItemDesc d on(i.sid=d.sid and i.itempos=d.itempos) where i.SID = ? and i.ItemSID != 1000000005', (r['sid'],))
    for s in sur_pos.fetchall():
        itemsid,clerk,price,price_tax,qty,deptsid,cost = s
        
        qty = float(qty)
        price = float(price)
        price_tax = float(price_tax)
        cost = float(cost)
        if r['receipttype'] > 0:
            price = -price
            price_tax = -price_tax
            cost = -cost
        
        price = round(price * qty * rate, 5)
        price_tax = round(price_tax * qty * rate, 5)
        total_price_tax += price_tax

        #fallback
        if cost:
            cost = round(cost * qty, 5)
        else:
            cost = price
        
        cate = (g_depts.get(deptsid) or [None, None])[1]
        if cate == None: cate = (g_item_depts.get(itemsid) or [None, None])[1]
        
        items.append( (itemsid, clerk.lower(), price, qty, cate, cost) )
    
    r['is_invoice'] = bool(not is_local_reversed and round(total_price_tax, 2) > 0 and acct_amt)
    r['items'] = items

g_depts = {}
cur_pos.execute('select sid,deptname from department where datastate=0')
for r in cur_pos.fetchall():
    cate = const.ITEM_D_DEPT.get(r[1].lower())
    g_depts[r[0]] = (r[1], cate)
    
g_item_depts = {}
cur_pos.execute('select itemsid,deptsid from inventory where datastate=0')
for r in cur_pos.fetchall():
    g_item_depts[ r[0] ] = g_depts.get(r[1])
    
g_receipts = {}
cur_pos.execute("select sid,ReceiptRefSID,ReceiptNum,ReceiptType,ReceiptStatus,Clerk,TenderType,QBFSStatus,DiscAmount,SubTotal,ReceiptDate"
            + " from Receipt r where datastate = 0 and ReceiptType < 2 and ReceiptDate >= ? and ReceiptDate < ? order by receiptnum asc",
            (g_from_date, g_to_date)
            )
col_nzs = [ d[0].lower() for d in cur_pos.description ]
for r in cur_pos.rows():
    r = dict(zip(col_nzs, r))
    parse_receipt(r)
    r['included'] = True
    
    if not r['qbfsstatus']: print_err('unreliable, receipt(%d) not transfered yet!', rnum)
    g_receipts[ r['receiptnum'] ] = r

g_qb_invoices = []
regx_posnum = re.compile('pos receipt #([0-9]+)', re.S|re.I|re.M)
cur_qb.execute("select h.transaction_id,l.memo,h.transaction_date,h.doc_num from abmc_invoice_header h left join abmc_invoice_lineitem l on(h.transaction_id=l.transaction_id and h.target_id=l.target_id) where h.is_paid_bool = 1 and h.transaction_id in"
               + " (select transaction_id from abmc_transaction_link where link_type in (3,4,5,22) and is_t1_source_bool = 0 group by transaction_id having max(transaction_date) >= ? and max(transaction_date) < ?)",
               (g_from_date, g_to_date)
               )
for r in cur_qb.rows():
    tid,memo,tdate,docnum = r
    if not memo: continue
    m = regx_posnum.search(memo)
    if not m: continue
    rnum = int(m.group(1))
    
    r = g_receipts.get(rnum)
    if not r:
        sur_pos.execute('select ' + ','.join(col_nzs) + ' from Receipt where datastate = 0 and receipttype < 2 and receiptnum = ?',
                    (rnum, )
                    )
        r = sur_pos.fetchall()
        if not r: continue
        r = dict(zip(col_nzs, r[0]))
        parse_receipt(r)
        r['included'] = False
        
    if not r['is_invoice']: continue
    if is_inv_exists(rnum, g_from_date_mon):
        print_err('invoice(%d) marked as paid already!', rnum)
        continue
    if not r['included']: g_receipts[rnum] = r
    
    r['qb'] = (tid, tdate, docnum)
    g_qb_invoices.append( (rnum, g_from_date_mon, json.dumps(r['qb'], separators=(',',':'))) )


cur_mdb.execute('delete from invoicev2 where inv_date=%s', (g_from_date_mon,))
if g_qb_invoices: cur_mdb.executemany('insert ignore into invoicev2 values(%s,%s,%s)', g_qb_invoices)


USER_MAP = {
    'sales1': 'ray',
    'sales2': 'anthony',
    'sales3': 'joe',
    'sales8': 'nicole',
    'sales5': 'jimmy',
    'sales6': 'sally',
}

g_clerks = {}
g_numrec = {}
for num,r in g_receipts.items():
    is_invoice = r['is_invoice']
    included = r['included']
    
    if included:
        r_clerk = r['clerk'].lower()
        g_numrec.setdefault(USER_MAP.get(r_clerk, r_clerk), [0])[0] += (r['receipttype'] and -1 or 1)
    
    qb = r.get('qb')
    for itemsid, clerk, price, qty, cate, cost in r['items']:
        clerk = USER_MAP.get(clerk, clerk)
        p = g_clerks.setdefault(clerk, {}).setdefault(cate, [0, 0, 0,  0, 0, 0])
        
        profit = price - cost
        if included:
            if not is_invoice or qb:
                p[1] += price
                p[3 + 1] += profit
            else:
                p[0] += price
                p[3 + 0] += profit
        else:
            p[2] += price
            p[3 + 2] += profit


cPickle.dump( g_receipts, open(datafile_a, 'wb'), 1 )
cPickle.dump( (g_clerks, g_errs, g_numrec), open(datafile, 'wb'), 1 )
print "done"


