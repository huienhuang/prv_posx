import sys
import os
import glob
import json
import config
import cPickle
import const
import time

DEFAULT_PERM = 1 << config.USER_PERM_BIT['admin']
class RequestHandler(App.load('/basehandler').RequestHandler):

    def fn_default(self):
        pass
    
    
    