import json
import os
import time
import datetime
import sys
import config
import re



DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_default(self):
        self.req.writefile('view_item_mobile_v1.html')
        
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
        cur.execute('insert into item values(%s,0,%s) on duplicate key update rev=rev+1,imgs=%s', (
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
        
        self.req.writejs({'imgs':rows[0][0], 'sid':str(sid)})
        