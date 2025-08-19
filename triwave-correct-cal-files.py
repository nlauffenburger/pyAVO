# -*- coding: utf-8 -*-
"""
triwave correct
Nate Lauffenburger 2/8/2022
"""
import glob, logging, datetime, os,  csv
from pyAVO2.triwave_correct import TriwaveCorrect
from echolab2.instruments import EK80


# Parameterize some of the processing.  Later, we will allow user to pass these into this script or read from an init file
# Instrument name: 'EK60' or 'EK80'
instrument = 'EK80'

input_path = 'G:\\AVO\\Calibration - Logsheets - Quick Checks\\2025\\NW Explorer\\calibration-5-27-2025\\RawFiles\\'

output_path = 'G:\\AVO\\Calibration - Logsheets - Quick Checks\\2025\\NW Explorer\\calibration-5-27-2025\\NewCorrectedRawFiles\\'

triwave_params = {'start_sample': 0, 
                            'end_sample':2}

triwave_correcter = TriwaveCorrect(triwave_params['start_sample'], triwave_params['end_sample'])

# BEGIN PROCESSING CODE
#

# Set up logger
LOG_FORMAT = "%(asctime)s %(filename)s:%(lineno)-4d "\
                            "%(levelname)s %(message)s"
formatter = logging.Formatter(LOG_FORMAT)
try:
    os.mkdir(output_path+'logs')
    logging.info('Successful creation of folder: logs')
except: 
    logging.info('Folder logs already exists')
file_handler = logging.FileHandler(output_path+'logs\\log_{:%m-%d-%Y}.log'.format(datetime.datetime.now()))
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

# Find raw files in path
file_list = glob.glob(input_path+'*.raw')
num_of_files = len(file_list)

for file in file_list:
    base_name = file[file.rfind('\\')+1:-4]
    ek = EK80.EK80()
    ek.read_raw(file)
    for key, value  in ek.frequency_map.items():
        for data in ek.raw_data[value[0]]:
            data, fit_results, val = triwave_correcter.triwave_correct(data)
            
            
            logging.info('Triwave correction was performed successfully for '+value[0])
            file_name = output_path+'triwave_params.csv'
            if not os.path.exists(file_name):
                with open(file_name, 'a', newline='') as csvfile:
                    headers = ['file name', 'frequency', 'r squared', 'amplitude offset', 'amplitude', 'period offset']
                    csvwriter = csv.writer(csvfile, delimiter=',')
                    csvwriter.writerow(headers)

            with open(file_name, 'a', newline='') as csvfile:
                data_to_write = [base_name, value[0], fit_results['r_squared'], fit_results['amplitude_offset'], fit_results['amplitude'], fit_results['period_offset']]
                csvwriter = csv.writer(csvfile, delimiter=',')
                csvwriter.writerow(data_to_write)
            
            
    ek.write_raw(output_path+'Triwave-Corrected-'+base_name[0:3], overwrite=True)
        
        

