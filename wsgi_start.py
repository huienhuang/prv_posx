import tinywsgi2
import os
import sys


cur_dir = os.path.dirname(__file__)
sys.path.append(cur_dir)

import config
application = tinywsgi2.Application(True, config.APP_DIR, web_dir='/posx').application

