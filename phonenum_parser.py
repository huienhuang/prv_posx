import re

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
