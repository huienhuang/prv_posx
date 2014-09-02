import urllib
import urllib2
import Cookie
import re
import datetime
import json
import base64
import time
import config
import db

#-------------------------------------------------

tar_dt = datetime.date(2014, 8, 28)

#-------------------------------------------------

def getc(url, data, ck):
    s_ck = ck.output(header='', sep=';', attrs=[]).strip()
    print url
    
    req = urllib2.Request(url, data and urllib.urlencode(data) or None)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.143 Safari/537.36')
    #req.add_header('Accept-Encoding', 'gzip,deflate,sdch')
    req.add_header('Accept-Language', 'en-US,en;q=0.8')
    if s_ck: req.add_header('Cookie', s_ck)

    fp = urllib2.urlopen(req)
    s_ck = fp.headers.get('set-cookie')
    if s_ck: ck.load(s_ck)
    return fp.read()


regx_report = re.compile('<a href="(/CWRWeb/ReportNav.do?[^"]*)"[^>]*>Deposits</a>', re.I|re.S|re.M)
regx_pgfile = re.compile('popupwin\.location="(/ibi_apps/WFServlet\?PG_Func=pagehtml&PG_MRsaved=false&PG_File=[^"]*)";', re.I|re.S|re.M)
regx_tnlist = re.compile('<a href="([^"]*)"[^>]*>([0-9]{2})/([0-9]{2})/([0-9]{4})</a>', re.I|re.S|re.M)
regx_detail = re.compile('<tr>[^<]*<td[^>]*>([^<]*)</td>[^<]*<td[^>]*>([^<]*)</td>[^<]*<td[^>]*>([^<]*)</td>[^<]*<td[^>]*>([^<]*)</td>[^<]*<td[^>]*>([^<]*)</td>[^<]*</tr>', re.I|re.S|re.M)

data = json.loads(base64.b64decode(config.card_acct))

ck = Cookie.SimpleCookie()
c = getc('https://www.merchantconnect.com/CWRWeb/memberLogin.do', data, ck)
c = getc('https://www.merchantconnect.com' + regx_report.findall(c)[0], None, ck)
nk = Cookie.SimpleCookie(ck.output())
c = getc('https://www.merchantconnect.com/CWRWeb/ReportServlet', {'valid': 'true'}, nk)
c = getc('https://www.merchantconnect.com' + regx_pgfile.findall(c)[0].replace('PG_Func=pagehtml', 'PG_Func=ALLPAGES'), None, nk)

tar_dt_i = tar_dt.year * 10000 + tar_dt.month * 100 + tar_dt.day
rec = []
for r in regx_tnlist.findall(c):
    l,m,d,y = r
    dt_i = int(y) * 10000 + int(m) * 100 + int(d)
    if tar_dt_i != dt_i: continue
    
    c = getc(l, None, ck)
    nk = Cookie.SimpleCookie(ck.output())
    c = getc('https://www.merchantconnect.com/CWRWeb/ReportServlet', {'valid': 'true'}, nk)
    for j in regx_detail.findall(c):
        j = map(str.strip, j)
        print '> ', j
        if not j[1].isdigit(): continue
        
        m,d,y = map(int, j[0].split('/'))
        dt_i = int(y) * 10000 + int(m) * 100 + int(d)
        if tar_dt_i != dt_i: continue
        
        amt = round(float(j[4][1:].replace(',', '')), 2)
        
        rec.append( (j[1], j[2], j[3], amt) )




d_rec = {}
for r in rec: d_rec.setdefault(r[3], []).append(r)


dbc = db.db_mdb()
cur = dbc.cursor()

l_trans_not_found = []

cur.execute('select * from sync_receipts where order_date >=%s and order_date < %s order by creation_date asc', (
    int(time.mktime(tar_dt.timetuple())), int(time.mktime((tar_dt + datetime.timedelta(1)).timetuple()))
    )
)
nzs = cur.column_names
for r in cur.fetchall():
    r = dict(zip(nzs, r))
    
    r['gjs'] = json.load('global_js')
    
    for t in r['gjs']['tender']:
        if t['type'] not in (3, 4): continue
        amt = round(t['amount'], 2)
        
        l_rec = d_rec.get(amt)
        if not l_rec:
            l_trans_not_found.append( (t, r) )
            continue
        t['trans'] = l_rec.pop(0)
        

print '> Not Matched'
for t, r in l_trans_not_found:
    print 'RNum: %d, TransAmt: %0.2f' % (r['receiptnum'], t['amount'])

print "> The Rest"
for x in d_rec.values():
    for y in x:
        print y
        
        