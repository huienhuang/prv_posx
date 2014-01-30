import tinywsgi2
import os
import sys


app_dir = os.path.dirname(__file__)
sys.path.append(app_dir)
application = tinywsgi2.Application(True, app_dir, web_dir='/posx').application

