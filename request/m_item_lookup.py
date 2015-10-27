import json
import os
import time
import datetime
import sys
import config
import re
#import sqlanydb


CFG = {
    'id': 'M_ITEM_LOOKUP_C00E1007',
    'name': 'Mobile Item Lookup',
    'perm_list': [
    ('access', ''),
    ]
}


FLAG_ITEM_REQ_CHK = (1 << 3) | (1 << 4) | (1 << 5)

TICKET_TYPE_MAPPING = {1: 24, 2: 25, 50: 26}
TICKET_TYPE_MAPPING_R = dict([(f_v[1], f_v[0]) for f_v in TICKET_TYPE_MAPPING.items()])
    

class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        r = {'mode': config.settings['mode'], 'store_id': config.store_id}
        self.req.writefile('view_item_mobile_v1.html', r)
    
    def fn_search_item(self):
        kw = self.qsv_str('term')
        if not kw: return
        mode = self.qsv_int('mode')
        mini = self.qsv_int('mini')
        self.req.writejs( self.search_item(kw, mode, mini and 4 or 10) )
    
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
        
        if TICKET_TYPE_MAPPING_R.has_key(idx):
            self.req.psd()['type'] = [ str(TICKET_TYPE_MAPPING_R.get(idx)) ]
            self.req.redirect_i('problemtracker', 'new_ticket')
        
        cur = self.cur()
        if on:
            cur.execute('insert into item (sid,inv_flag) values(%s,%s) on duplicate key update inv_flag=inv_flag|%s', (
                sid, 1 << idx, 1 << idx
                )
            )
        else:
            #update only
            cur.execute('update item set inv_flag=inv_flag&%s where sid=%s', (
                ~(1 << idx), sid
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
        if rows: flag = rows[0][0] & 0x00FFFFFF

        cur.execute('select type,count(*) from tracker where sid=%s and state=0 group by type', (sid, ))
        for r in cur.fetchall():
            idx = TICKET_TYPE_MAPPING.get(r[0])
            if idx == None: continue
            if r[1]: flag |= 1 << idx
        
        self.req.writejs({'flag': flag})

    def fn_get_lst_item_chg_hist(self):
        ret = {'res':{'len':0, 'apg':[]}}
        
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            users = dict([(v[0], v[1])for v in self.getuserlist()])
            
            cur.execute(('select SQL_CALC_FOUND_ROWS si.num,si.name,h.qtynew,h.qtynew-h.qtydiff,u.user_name,ch.js,h.docdate,h.itemsid from item_chg_hist ch left join user u on (ch.user_id=u.user_id) left join sync_items_hist h on (ch.ch_id=h.sid and h.sid_type=2) left join sync_items si on (h.itemsid=si.sid) order by ch.ch_id desc limit %d,%d') % (
                        sidx * pgsz, (eidx - sidx) * pgsz
                        )
            )
            for r in cur.fetchall():
                r = list(r)
                r[5] = ', '.join([ "%d %s%s" % (f_x[2], f_x[0], f_x[1] != 1 and '(*%0.1f)' % (f_x[1],) or '') for f_x in json.loads(r[5]) ])
                r[-2] = time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(r[-2]))
                r[-1] = str(r[-1])
                apg.append(r)
                
            cur.execute('select FOUND_ROWS()')
        else:
            cur.execute('select count(*) from item_chg_hist')
        
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
    
    def fn_clear_item_chk(self):
        sid = self.req.psv_int('sid')
        cur = self.cur()
        cur.execute('update item set inv_flag=inv_flag&%s where sid=%s', (
            ~FLAG_ITEM_REQ_CHK, sid
            )
        )
        rc = cur.rowcount
        self.req.writejs({'err': int(not (rc > 0))})
    
    def fn_get_item_chk_lst(self):
        ret = {'res':{'len':0, 'apg':[]}}
        pgsz = self.qsv_int('pagesize')
        sidx = self.qsv_int('sidx')
        eidx = self.qsv_int('eidx')
        if pgsz > 100 or eidx - sidx > 5: self.req.exitjs(ret)
        
        cur = self.cur()
        apg = []
        if pgsz > 0 and sidx >= 0 and sidx < eidx:
            cur.execute('select SQL_CALC_FOUND_ROWS i.sid,i.inv_flag,i.imgs,si.num,si.name from item i left join sync_items si on (i.sid=si.sid) where i.inv_flag&%d!=0 order by i.sid desc limit %d,%d' % (
                FLAG_ITEM_REQ_CHK, sidx * pgsz, (eidx - sidx) * pgsz
                )
            )
            for r in cur.fetchall():
                sid,inv_flag,imgs,num,name = r
                
                desc = []
                if inv_flag & (1 << 3): desc.append('Barcode')
                if inv_flag & (1 << 4): desc.append('Price')
                if inv_flag & (1 << 5): desc.append('All')
                
                img = ""
                if imgs: img = imgs.split('|')[0]
                
                apg.append((
                    img,
                    num,
                    name,
                    ', '.join(desc),
                    'X',
                    str(sid)
                    )
                )
        
            cur.execute('select FOUND_ROWS()')
            
        else:
            cur.execute('select count(*) from item where inv_flag&%d!=0' % (
                FLAG_ITEM_REQ_CHK,
                )
            )
            
        rlen = int(cur.fetchall()[0][0])
        res = ret['res']
        res['len'] = rlen
        res['apg'] = apg
        self.req.writejs(ret)
        
    
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
        
        
    def set_item_qty(self):
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
