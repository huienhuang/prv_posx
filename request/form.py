import json
import os
import time
import datetime
import sys
import config
import re
#import sqlanydb


CFG = {
    'id': 'FORM_C00D1118',
    'name': 'FORM',
    'perm_list': [
    ('access', ''),
    ]
}


class RequestHandler(App.load('/advancehandler').RequestHandler):
    
    def fn_default(self):
        r = {}
        self.req.writefile('form_ctn.html', r)


    def fn_get_form(self):
        self.req.writefile('form/delivery.html')

    def fn_get_form_data(self):
        f_id = self.qsv_int('id')
        cur = self.cur()
        cur.execute('select * from form where id=%s', (f_id,))
        row = cur.fetchall()
        row = dict(zip(cur.column_names, row[0]))
        row['js'] = json.loads(row['js'])
        row['js']['id'] = f_id

        self.req.writejs(row)

    def fn_get_form_list(self):
        cur = self.cur()
        cur.execute('select * from form order by id desc')
        rows = []
        for r in cur.fetchall():
            r = dict(zip(cur.column_names, r))
            rows.append(r)

        self.req.writejs(rows)

    def fn_save(self):
        js = self.req.psv_js('js')

        f_type = int(js['type'])



        f_name = js['form']['name']
        f_id = int(js.get('id') or 0)
        


        cur = self.cur()

        cts = int(time.time())
        form_js = json.dumps(js['form'], separators=(',',':'))
        if f_id:
            cur.execute('update form set name=%s,keyword=%s,js=%s where id=%s', (
                f_name, f_name, form_js, f_id
            ))
        else:
            cur.execute('insert into form values(null, %s, %s, %s, %s, %s)', (
                f_name, f_name, self.user_id, cts, form_js
            ))

            f_id = cur.lastrowid

        self.req.writejs({'id': f_id})

