# -*- coding: utf-8 -*-
'''
load-AVO is designed to load exported CSV files from EV to the database (avobase)
Most of the code was ported over from the original pyAVO, adjusting for python 3 changes.

Nate Lauffenburger 2/8/2022

load_ev.py is the command line entry point to the pyAVO raw data loading processor.
Parameters are provided by at the beginning of this code

'''

import logging,  datetime
from pyAVO2 import csv_loader,  avo_db

# Specify frequency to load
frequency = 38000

# csv output directory from EV exports (no slashes at the end)
csvDir = 'G:\\AVO\\EV Files and exports\\bottom-referenced\\2021\\AKN_exports\\SS_11\\16m_to_3m_off_bottom\\'

# Specify database credentials for connection
load_params = {'user':'avobase2', 'schema':'avobase2', 
                'password':'Pollock#2468','dsn':'afsc',
                'survey_id':202106, 'ship_id':454}
                
#  specify the EV export format to use. Valid values are 0 or 1. I think early exports
#  lacked a few fields and are format 0. More recent exports are format 1.
csvFormat = 1

# BEING PROCESSING
#Setup logging
formatter = logging.Formatter(u'%(asctime)s::%(name)8s::%(levelname)8s::%(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logging.getLogger('').addHandler(stream_handler)

fh = logging.FileHandler(csvDir+'\\load_ev_log_{:%m-%d-%Y}.log'.format(datetime.datetime.now()))
fh.setFormatter(formatter)
logging.getLogger('').addHandler(fh)
logging.getLogger('').setLevel(logging.INFO)

#  start the AVO csv loading procedure
logging.info('---------------------------: STARTING PROCESSING :---------------------------')

#  open the database connection
logging.info('Opening connection to the database...')
db_connect = avo_db.Connection(user=load_params['user'], password=load_params['password'], 
                        dsn=load_params['dsn'], schema=load_params['schema'])

#  kick off the processor...
logging.info('Starting processing...')
csv_loader.process_ev_exports(survey_id=load_params['survey_id'], ship_id=load_params['ship_id'], csv_dir=csvDir, 
                                            db_connection=db_connect, frequency=frequency, csv_filename_regex_fmt=csvFormat)

