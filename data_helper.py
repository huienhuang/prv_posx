import re
import hashlib
import struct
import base64
import zlib

regx_phonenum = re.compile('[^0-9]+')
regx_phonenum_spliter = re.compile('[^\s\.\-0-9]+')
def parse_phone_num(p):
    p = p.strip()
    if not p: return ''
    
    nums = []
    nums_unk = []
    for a in regx_phonenum_spliter.split(p):
        a = a.strip()
        if not a: continue
        x = regx_phonenum.sub('', a)
        if not x or len(x) not in (7, 10, 11):
            nums_unk.append(a)
        else:
            nums.append( x[-7:] )
    
    if nums: return ','.join(nums)
    
    nums_unk_f = []
    for x in nums_unk:
        x = ' '.join([ s for s in regx_phonenum.split(x) if len(s) > 1 ])
        nums_unk_f.append(x)
        
    return ','.join(nums_unk_f)


def unify_location(args):
    return [ unicode(f_x or u'').strip().lower() for f_x in args ]

def get_location_hash(*args):
    args = unify_location(args)
    street = args[0]
    if not street: return None
    
    s = u','.join(args)
    return base64.b64encode(hashlib.md5(s).digest() + struct.pack('<L', zlib.crc32(s) & 0xFFFFFFFF))


def get_receipt_crc(r, jsd, items):
    v = unicode((
        sorted((jsd.get('customer') or {}).items()),
        sorted((jsd.get('shipping') or {}).items()),
        jsd['memo'],
    )).encode('utf-8')
    return zlib.crc32(v) & 0xFFFFFFFF

def get_salesorder_crc(r, jsd, items):
    v = unicode((
        sorted((jsd.get('customer') or {}).items()),
        sorted((jsd.get('shipping') or {}).items()),
        jsd['memo'],
        r['clerk'],
        r['sonum'],
        r['sodate'],
        r['pricelevel'],
        r['datastate'],
        jsd['total'], jsd['subtotal'], jsd['deposittaken'],
        
        [ (f_i['itemsid'], f_i['itemno'], f_i['snum'], f_i['desc1'], f_i['uom'], f_i['alu'], f_i['pricetax'], f_i['qty']) for f_i in items ]
    )).encode('utf-8')
    return zlib.crc32(v) & 0xFFFFFFFF

