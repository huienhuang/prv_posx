import tinywsgi3 as wsgi
import os
import sys


cur_dir = os.path.dirname(__file__)
sys.path.append(cur_dir)

import config
application = wsgi.Application(True, config.APP_DIR, web_dir='/posx', als={'dbrefs': []}).application

