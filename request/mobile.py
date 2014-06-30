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
        if not rows:
            imgs = ''
        else:
            imgs = rows[0][0] or ''
            
        self.req.writejs({'imgs':imgs, 'sid':str(sid)})
        
        
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
        return
    
    
        sid = self.req.psv_int('sid')
        cur_qty = round(float(self.req.psv_ustr('cur_qty')), 2)
        in_units = [ [f_x[0], float(f_x[1]), int(f_x[2] or 0)] for f_x in self.req.psv_js('js') ]
        
        cur = self.cur()
        cur.execute("select detail from sync_items where sid=%s", (sid,))
        rows = cur.fetchall()
        if not rows: return
        jsd = json.loads(rows[0][0])
        units = [ [u[2].lower(), u[3]] for u in jsd['units'] if u[3] ]
        if len(units) != len(in_units): return

        new_qty = 0
        for i in range(len(units)):
            u = in_units[i]
            if units[i][:2] != u[:2]: return
            new_qty += float(u[1]) * int(u[2] or 0)
        new_qty = round(new_qty, 2)
        
        if cur_qty == new_qty:
            self.req.exitjs({'err': 2, 'err_s': 'same value, nothing to do'})
            return
        
        cur_ts = int(time.time())
        ret = self.modify_item_qty(sid, cur_qty, new_qty)
        if ret:
            cur.execute('insert into item_chg_hist values(null,%s,%s)', (
                self.user_id, json.dumps(in_units, separators=(',',':'))
            ))
            ch_id = cur.lastrowid
            cur.execute('insert into sync_items_hist values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', (
                ch_id, 2, sid, ch_id, ch_id, 4 << 8,
                "Adj.(New:%0.1f Old:%0.1f) By %s" % (new_qty, cur_qty, self.user_name,),
                new_qty,
                round(new_qty - cur_qty, 2),
                0, 0, 0,
                cur_ts
            ))
        
        self.req.writejs({'err': int(not ret)})
    
    fn_set_item_qty.PERM = 1 << config.USER_PERM_BIT['adj item qty']
    
    
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
