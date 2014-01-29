import json
import os
import time
import config
import re
import datetime
import traceback


DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/basehandler').RequestHandler):

    OF_PAID = 1 << 8
    OF_PAYABLE = 1 << 16
    OF_CLOSE = 1 << 3
    OF_REVERSED = 1 << 2 #REVERSED Or Regular
    OF_REVERSING = 1 << 1 #REVERSING OR Regular
    OF_COMPLETED = 1 << 0
    
    def fn_default(self):
        d = {
            'userlist': self.getuserlist(),
            'user_lvl': self.user_lvl,
            'user_id': self.user_id,
        }
        self.req.writefile('receiptstat.html', d)

    def fn_stat(self):
        assoc_id = self.qsv_int('assoc_id')
        from_ts = self.qsv_int('from_ts')
        to_ts = self.qsv_int('to_ts')
        status = self.qsv_int('status')
        
        s_flag = 'i.ord_flag&%d!=0' % (self.OF_CLOSE,)
        if status == 1:
            s_flag += ' and (i.ord_flag&%d!=0 or i.ord_flag&%d=0)' % (self.OF_REVERSING|self.OF_REVERSED|self.OF_PAID, self.OF_PAYABLE)
        elif status == 2:
            s_flag += ' and (i.ord_flag&%d=0 and i.ord_flag&%d!=0)' % (self.OF_REVERSING|self.OF_REVERSED|self.OF_PAID, self.OF_PAYABLE)
        
        db = self.db()
        cur = db.cur()
        db_col_nzs = ['ord_id', 'ord_flag', 'ord_assoc_id', 'ord_order_date', 'ord_creation_date', 'ord_global_js', 'user_name']
        if not assoc_id: db_col_nzs.append('ord_items_js')
        cur.execute('select i.ord_id,i.ord_flag,i.ord_assoc_id,i.ord_order_date,i.ord_creation_date,i.ord_global_js,u.user_name'+(not assoc_id and ',i.ord_items_js' or '')+' from sorder i left join user u on (i.ord_assoc_id=u.user_id) where %s and i.ord_creation_date>=%d and i.ord_creation_date<%d%s order by i.ord_id desc' % (
            s_flag,
            from_ts,
            to_ts + 3600 * 24,
            assoc_id and ' and i.ord_assoc_id=%d' % (assoc_id, ) or '',
            )
        )
        stat = []
        rows = cur.fetchall()
        if assoc_id:
            total = 0
            cost = 0
            count = 0
            for r in rows:
                r = dict(zip(db_col_nzs, r))
                flag = int(r['ord_flag'])
                if flag & self.OF_REVERSING:
                    r_type = 'Reversing'
                elif flag & self.OF_REVERSED:
                    r_type = 'Reversed'
                else:
                    r_type = 'Regular'
                    
                if not (flag & (self.OF_REVERSING | self.OF_REVERSED)) and (flag & self.OF_PAYABLE):
                    if flag & self.OF_PAID:
                        paid_s = 'Y'
                    else:
                        paid_s = 'N'
                else:
                    paid_s = '-'
            
                js = json.loads(r['ord_global_js'])
                order_date_ts = int(r['ord_order_date'])
                creation_date_ts = int(r['ord_creation_date'])
                stat.append({
                    'id': int(r['ord_id']),
                    'type': r_type,
                    'paid': paid_s,
                    'order_date': time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(order_date_ts)),
                    'creation_date': order_date_ts != creation_date_ts and time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(creation_date_ts)) or None,
                    'total': js['total'],
                    'memo': js['memo'].split('\n', 2)[0].strip(),
                })
            
                if flag & self.OF_REVERSING:
                    total -= js['total']
                else:
                    total += js['total']
                total = round(total, 2)
                count += 1
            
        else:
            stat = {}
            total = 0
            cost = 0
            count = 0
            for r in rows:
                r = dict(zip(db_col_nzs, r))
                
                r_cost = config.round_ex(sum([ t['prev_qty'][4] * t['in_base_qty'] for t in json.loads(r['ord_items_js']) ]))
                
                uid = int(r['ord_assoc_id'])
                s = stat.setdefault(uid, {'uid':uid, 'name':r['user_name'], 'total':0, 'count':0, 'cost':0})
                js = json.loads(r['ord_global_js'])
                
                flag = int(r['ord_flag'])
                if flag & self.OF_REVERSING:
                    total -= js['total']
                    cost -= r_cost
                    s['total'] -= js['total']
                    s['cost'] -= r_cost
                else:
                    total += js['total']
                    cost += r_cost
                    s['total'] += js['total']
                    s['cost'] += r_cost
                count += 1
                s['count'] += 1
                
            stat = sorted(stat.values(), key=lambda a:(a['name'], a['uid']))
            for s in stat: s['total'] = round(s['total'], 2)
            
        self.req.writejs({
            'assoc_id': assoc_id,
            'stat': stat,
            'total': round(total, 2),
            'count': count,
            'cost': cost
            })

