import config
import db as mydb

mdb = mydb.db_mdb()
cur = mdb.cursor()


cur.execute("delete from item where inv_flag=0 and (imgs='' or imgs is null)")
cur.execute("delete from item where sid not in (select sid from sync_items)")

print "Done"


