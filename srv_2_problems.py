import db as mydb
import os
import json

cur_dir = os.getcwd()

db = mydb.db_pos()
cur = db.cursor()
sur = db.cursor()

print "looking for wrong date receipts..."

sql = "select ReceiptNum,Cashier,convert(numeric(19,2),SubTotal-DiscAmount),ReceiptDate+ReceiptTime,CreationDate,SID from receipt where DataState=0 and ReceiptDate != date(CreationDate)"
cur.execute(sql)
d = cur.fetchall()

json.dump(d, open( os.path.join(cur_dir, 'data', 'wrongdate.txt'), 'wb'))


print "looking for error quantity items..."


sql = "select ItemNO,convert(numeric(19,2),QtyStore1),Desc1 from Inventory where DataState=0 and QtyStore1 <= 0 order by lastedit desc"
cur.execute(sql)
d = cur.fetchall()
json.dump(d, open( os.path.join(cur_dir, 'data', 'errorquantity.txt'), 'wb'))


print "looking for error price items..."

d = []
sql = "select ItemSID,ItemNO,Desc1,Cost,Price1 from Inventory where DataState=0 order by lastedit desc"
cur.execute(sql)
for r in cur.rows():
    itemsid,itemno,desc,cost,price = r
    cost = float(cost)
    price = float(price)
    sur.execute('select UnitOfMeasure,convert(numeric(19,2),UnitFactor),convert(numeric(19,2),Price1) from InventoryUnits where ItemSID=? and (UnitFactor < 1.0 or Price1 < UnitFactor * ?) order by UOMPos asc',
                (itemsid, cost)
                )
    uom = sur.fetchall()
    
    if uom or price < cost:
        d.append([itemno, "%0.2f" % (price,), ', '.join(['|'.join(i) for i in uom]), desc])
        
json.dump(d, open( os.path.join(cur_dir, 'data', 'errorprice.txt'), 'wb'))





