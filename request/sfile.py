import json
import os
import time
import datetime
import sys
from PIL import Image
import hashlib
import struct
import base64
import config
import cStringIO


CFG = {
    'id': 'SFILE_AA000007',
    'name': 'File Storage',
    'perm_list': [
    ('access', ''),
    ]
}


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

class RequestHandler(App.load('/basehandler').RequestHandler):
    
    def fn_upload_img(self):
        psd = self.req.psd()
        if not psd.has_key('img'): return
        
        img = psd['img']
        if type(img) == type([]): img = img[0]
        if not img.file: return
        
        now = datetime.datetime.now()
        sdir = config.SFILE_DIR + '/upload/%04d%02d/%02d' % (now.year, now.month, now.day)
        wdir = 'file/upload/%04d%02d/%02d' % (now.year, now.month, now.day)
        try:
            os.makedirs(sdir)
        except:
            pass
        
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
        
        fnz = base64.urlsafe_b64encode(struct.pack('L', int(time.time())) + hashlib.md5(os.urandom(128)).digest())
        
        
        nim.thumbnail((1200, 1200), Image.ANTIALIAS)
        nim.save('%s/%s.jpg' % (sdir, fnz), "JPEG", quality=82)
        nim.thumbnail((200, 200), Image.ANTIALIAS)
        nim.save('%s/%s_200.jpg' % (sdir, fnz), "JPEG", quality=82)
        
        lst = json.dumps( (('IMG', '%s/%s_200.jpg' % (wdir, fnz)),) )
        self.req.writefile('finish_upload_img.html', {'lst': lst})
        
    
    def fn_upload_img_v1(self):
        img = base64.b64decode(self.req.psv_ustr('img'))
        
        now = datetime.datetime.now()
        sdir = config.SFILE_DIR + '/upload/%04d%02d/%02d' % (now.year, now.month, now.day)
        wdir = 'file/upload/%04d%02d/%02d' % (now.year, now.month, now.day)
        try:
            os.makedirs(sdir)
        except:
            pass
        
        im = Image.open(cStringIO.StringIO(img))
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
        
        fnz = base64.urlsafe_b64encode(struct.pack('L', int(time.time())) + hashlib.md5(os.urandom(128)).digest())
        
        nim.thumbnail((1200, 1200), Image.ANTIALIAS)
        nim.save('%s/%s.jpg' % (sdir, fnz), "JPEG", quality=82)
        nim.thumbnail((200, 200), Image.ANTIALIAS)
        nim.save('%s/%s_200.jpg' % (sdir, fnz), "JPEG", quality=82)
        
        self.req.writejs( (('IMG', '%s/%s_200.jpg' % (wdir, fnz)),) )
        
        