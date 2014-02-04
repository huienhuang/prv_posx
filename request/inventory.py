import json
import os
import time
import config
import datetime
import sys

DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_view_item_mobile(self):
        self.req.write(str(sys.path))
        #self.req.writefile('view_item_mobile.html')
    
    
    def fn_upload_img(self):
        psd = self.req.psd()
        if not psd.has_key('img'): return
        
        img = psd['img']
        if type(img) == type([]): img = img[0]
        if not img.file: return
            
        import Image
        im = Image.open("d:/upload.png")
        im.thumbnail((200, 200), Image.ANTIALIAS)
        im.save("d:/pk.jpeg", "JPEG", quality=82)
        
        self.req.writefile('finish_upload_img.html', {'lst':''})
        
        