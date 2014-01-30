import mysql.connector
import config

class MySQLRef:
    def __init__(self, dbc):
        self.dbc = dbc
        self.curs = []
    
    def commit(self):
        self.dbc.commit()
        
    def cur(self, new=False):
        if len(self.curs) <= 0 or new:
            cur = self.dbc.cursor()
            self.curs.append(cur)
            return cur
        else:
            return self.curs[0]
    
    def close_curs(self):
        for cur in self.curs:
            try:
                cur.close()
            except:
                pass
        self.curs = []
    
    def close_dbc(self):
        self.close_curs()
        if self.dbc:
            try:
                self.dbc.close()
            except:
                pass
            self.dbc = None
    
    def __del__(self):
        self.close_dbc()

def get(req):
    dbref = req.rls.get('dbref')
    if dbref: return dbref
    
    dbrefs = req.app.als.setdefault('dbrefs', [])
    try:
        dbref = dbrefs.pop()
        try:
            cur = dbref.cur()
            cur.execute('select 1')
            cur.fetchall()
        except:
            dbref = None
                
    except IndexError, e:
        dbref = None
        
    if not dbref:
        dbc = mysql.connector.connect(**config.mysql)
        dbref = MySQLRef(dbc)
        
    req.rls['dbref'] = dbref
    return dbref

def put(req):
    dbref = req.rls.get('dbref')
    if dbref:
        req.rls['dbref'] = None
        try:
            dbref.dbc.rollback()
        except:
            pass
        dbref.close_curs()
        req.app.als['dbrefs'].append(dbref)

