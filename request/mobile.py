import json
import os
import time
import datetime
import sys
import config
import re
import sqlanydb


DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        r = {'mode': config.settings['mode']}
        self.req.writefile('view_item_mobile_v1.html', r)
        
    REGX_FNZ_SUB = re.compile("[^0-9a-z-_=]", re.I|re.M|re.S)
    def fn_set_imgs(self):
        sid = self.req.psv_int('sid')
        imgs = self.req.psv_ustr('imgs').split('|')
        
        lst = []
        for img in imgs:
            img = img.strip()
            if not img: continue
            d_yr,d_day,fnz = img[12:].split('/', 3)
            fnz = self.REGX_FNZ_SUB.sub('', fnz[:-4])
            if not d_yr.isdigit() or not d_day.isdigit() or not fnz: continue
            if not os.path.exists( os.path.join(config.SFILE_DIR, 'upload', d_yr, d_day, fnz + '.jpg') ): continue
            
            img = 'file/upload/%s/%s/%s.jpg' % (d_yr, d_day, fnz)
            lst.append(img)
        
        imgs = '|'.join(lst)
        cur = self.cur()
        cur.execute('insert into item (sid,rev,imgs) values(%s,0,%s) on duplicate key update rev=rev+1,imgs=%s', (
            sid, imgs, imgs
            )
        )
        
        self.req.writejs({'sid':str(sid), 'ret':1})
    
    def fn_get_imgs(self):
        sid = self.req.psv_int('sid')
        
        cur = self.cur()
        cur.execute('select imgs from item where sid=%s', (sid,))
        rows = cur.fetchall()
        if not rows: return
        
        self.req.writejs({'imgs':rows[0][0] or '', 'sid':str(sid)})
        
        
    def fn_set_single_inv_flag(self):
        sid = self.req.psv_int('sid')
        idx = self.req.psv_int('idx')
        on = self.req.psv_int('on')
        if idx < 0 or idx > 31: return
        
        cur = self.cur()
        if on:
            cur.execute('insert into item (sid,inv_flag) values(%s,%s) on duplicate key update inv_flag=inv_flag|%s', (
                sid, 1 << idx, 1 << idx
                )
            )
        else:
            #update only
            cur.execute('insert into item (sid,inv_flag) values(%s,%s) on duplicate key update inv_flag=inv_flag&%s', (
                sid, 0, ~(1 << idx)
                )
            )
        
        rc = cur.rowcount
        self.req.writejs({'err': int(not (rc > 0))})
        
    def fn_get_inv_flag(self):
        sid = self.req.psv_int('sid')
    
        cur = self.cur()
        cur.execute('select inv_flag from item where sid=%s', (sid,))
        rows = cur.fetchall()
        flag = 0
        if rows: flag = rows[0][0]
            
        self.req.writejs({'flag': flag})
        
    """
    def fn_get_inv_rec(self):
        sid = self.req.psv_int('sid')
        cur = self.cur()
        cur.execute("select detail from sync_items where sid=%s", (sid,))
        rows = cur.fetchall()
        if not rows: return
        
        ret = {}
        js = json.loads(rows[0][0])
        ret['pos_qty'] = js['qty'][0]
        ret['units'] = units = [ (u[2].lower(), u[3]) for u in js['units'] if u[3] ]
        
        cur.execute("select r.*,u.user_name from item_qty_rec r left join user u on (r.user_id=u.user_id) where r.sid=%s", (sid,))
        rows = cur.fetchall()
        if rows:
            cnz = cur.column_names
            r = dict(zip(cnz, rows[0]))
            jss = json.loads(r['js'])
            del r['js']
            
            u_units = jss['units']
            matched = False
            if len(units) == len(u_units):
                matched = True
                for i in range(len(units)):
                    if u_units[i][:2] != units[:2]:
                        matched = False
                        break
            
            if matched:
                r['time'] = time.strftime("%m/%d/%y %I:%M:%S %p", time.localtime(r['ts']))
                r['units'] = u_units
                
                ret['rec'] = r
    
        self.req.writejs(ret)
    
    def fn_set_inv_rec(self):
        pass
    """
    
    def fn_get_item_unit(self):
        sid = self.req.psv_int('sid')
        cur = self.cur()
        cur.execute("select detail from sync_items where sid=%s", (sid,))
        rows = cur.fetchall()
        if not rows: return
        
        jsd = json.loads(rows[0][0])
        js = {}
        js['qty'] = jsd['qty'][0]
        js['units'] = units = [ (u[2].lower(), u[3]) for u in jsd['units'] if u[3] ]
        
        self.req.writejs(js)
        
        
    def fn_set_item_qty(self):
        sid = self.req.psv_int('sid')
        cur_qty = float(self.req.psv_ustr('cur_qty'))
        in_units = self.req.psv_js('js')
        
        cur.execute("select detail from sync_items where sid=%s", (sid,))
        rows = cur.fetchall()
        if not rows: return
        jsd = json.loads(rows[0][0])
        units = [ (u[2].lower(), u[3]) for u in js['units'] if u[3] ]
        
        if len(units) != len(in_units): return
        new_qty = 0
        for i in range(len(units)):
            u = in_units[i]
            if units[i][:2] != u[:2]: return
            new_qty += u[1] * int(u[2] or 0)
        
        #ret = self.modify_item_qty(sid, cur_qty, new_qty)
        
        self.req.writejs({'err': int(not ret)})
    
    def modify_item_qty(self, sid, old_qty, new_qty):
        dbc = sqlanydb.connect(**config.sqlany_pos_server)
        
        try:
            cur = dbc.cursor()
            cur.execute('update inventory set lastedit=now() where itemsid=? and datastate=0 and QtyStore1-CustOrdQty=AvailQty and CompanyOHQty=QtyStore1 and CompanyOHQty=?', (
                sid, old_qty
                )
            )
            cur.execute('select @@rowcount')
            if cur.fetchall()[0][0] <= 0: return False
            
            cur.execute('select ReorderNotNull,CompanyOHQty,CustOrdQty,CmpMin,TotO_O from inventory where itemsid=?', (sid,))
            ReorderNotNull,CompanyOHQty,CustOrdQty,CmpMin,TotO_O = map(float, cur.fetchall()[0])
            CompanyOHQty_new = new_qty
            AvailQty_new = CompanyOHQty_new - CustOrdQty
            if ReorderNotNull:
                if AvailQty_new + TotO_O <= CmpMin:
                    BelowReorder_new = 1
                else:
                    BelowReorder_new = 0
                cur.execute('update inventory set BelowReorder=?,CompanyOHQty=?,QtyStore1=?,AvailQty=?,lastedit=now() where itemsid=?', (
                    BelowReorder_new,
                    CompanyOHQty_new,
                    CompanyOHQty_new,
                    AvailQty_new,
                    sid,
                    )
                )
            else:
                cur.execute('update inventory set CompanyOHQty=?,QtyStore1=?,AvailQty=?,lastedit=now() where itemsid=?', (
                    CompanyOHQty_new,
                    CompanyOHQty_new,
                    AvailQty_new,
                    sid,
                    )
                )
            cur.execute("insert into changejournal values(default,'Inventory',?,1,now(),'POSX', '-1')", (sid,))
            cur.execute('commit')
        
            return True
        except:
            pass
        
        finally:
            try:
                dbc.close()
            except:
                pass
            
        return False
