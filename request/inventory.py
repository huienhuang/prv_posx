import json
import os
import time
import config
import datetime
import sys
import Image


ORIENTATION = [
    None, None,
    (Image.FLIP_LEFT_RIGHT), #2
    Image.ROTATE_180, #3
    Image.FLIP_TOP_BOTTOM, #4
    (Image.FLIP_TOP_BOTTOM, Image.ROTATE_270), #5
    Image.ROTATE_270, #6
    (Image.FLIP_LEFT_RIGHT, Image.ROTATE_270), #7
    Image.ROTATE_90 #8
]


DEFAULT_PERM = 0x00000001
class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_view_item_mobile(self):
        self.req.writefile('view_item_mobile.html')
    
    
    def fn_upload_img(self):
        psd = self.req.psd()
        if not psd.has_key('img'): return
        
        img = psd['img']
        if type(img) == type([]): img = img[0]
        if not img.file: return
        
        im = Image.open(img.file)
        try:
            orien = (im._getexif() or {}).get(0x0112, 1)
        except:
            orien = 1
        
        nim = im
        if orien >= 0 and orien < len(ORIENTATION):
            ori = ORIENTATION[orien]
            if ori != None:
                if type(ori) == tuple:
                    nim = im.transpose(ori[0])
                    nim = im.transpose(ori[1])
                else:
                    nim = im.transpose(ori)
        
        nim.thumbnail((1200, 1200), Image.ANTIALIAS)
        nim.save("e:/pk.jpg", "JPEG", quality=82)
        #im.thumbnail((200, 200), Image.ANTIALIAS)
        #im.save("e:/pk.jpg", "JPEG", quality=82)
        
        self.req.writefile('finish_upload_img.html', {'lst':''})
        
        