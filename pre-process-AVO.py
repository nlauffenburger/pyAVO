# -*- coding: utf-8 -*-
"""
pre-process-AVO is designed to perform operations (subsampling, filter, etc) on raw files 
and write them out as new 'ready-to-hand-process' files.  
**Tested for EK60, ES60 & EK80**

The steps that are currently included in the code are outlined below.
Any combination of these methods can be implemented by using the specified parameters.

1. Files can be combined based on a time unit (hour or day) or a file unit (number of files)
2. Triangle-wave correct (e.g. for ES60).
3. Subsampling based on percent, chunk size (# of pings), ping start, and number of iterations
4. Filtering out night-time data.
5. Filter out 'bad' dropout pings based on transmit pulse and/or bottom echo,
    typically caused by inclement weather.
5b. Rejection of ping subset chunks if the number of pings rejected in an averaging interval exceeds
    a percent threshold specified (e.g. if 15% of more of a 50 chunk are rejected, remove the chunk).
6. Filter out data outside a defined geographic region.
7. Filter out data below a specified speed threshold.
8. Reporting of triangle wave correction fit, subsampling, filtering, and gps data.

Extras:
9. Merging of out files to collect all 
10. For AVO, the data_files table, in the database (avobase) can be 'pre-loaded' with the processed
    data file names for both raw and out files, so that loading of hand-scrutinized data is possible.
11. Maps (still in beta) can be generated from the gps data when the final set of files is processed
    to display ship track highlighted by subsampling and filtering.
12. Echograms can be recorded.

Instead of creating an init file with runtime params, the first section of this script should be edited
to specify processing choices and data for each run is saved:
Runtime parameters are saved and log files are generated for each run.

Additional notes:  
* All data written into a subsample is labeled with the line number of the subsample
    (e.g. for all subsample 1, the file names are L0001)
* Processing can be started at a specified time (yyyymmdd hhmmss)
* This script initializes and runs process_data.py and merge_out_data.py.  Most of the code in this
    file sets up parameters, logging, initializes class, and organizes the files for processing.  The hard
    work is done in process_data and merge_out_data.
* To load exported data into the database (avobase) from hand-scrutinized EV files, see load-AVO.py

Nate Lauffenburger 2/8/2022
"""
import glob, logging, datetime, os
from pyAVO2.process_data import Process
from pyAVO2.merge_out_data import Merge
import numpy as np
import pandas as pd


# Parameterize some of the processing.  Later, we will allow user to pass these into this script or read from an init file
# Instrument name: 'EK60' or 'EK80'
instrument = 'EK60'
# Minimum number of pings left after filtering to write a new file
minimum_pings_to_write = 1
# write the original data with no subsampling or filter to reference.  A single file for the time/length specified will be output before subsampling & filtering
write_orig = False
# make a figure with echogram image of original data with no subsampling or filter for reference.
make_echogram = True
# save gps data and speed by ping for original file
save_gps = True
# primary frequency- process this channel first, match pings from other frequencies to this frequency and use subsampling index from this one for others
primary_frequency = 38000
# Combine out files into one that holds all bottom data for the output raw file.
# This isn't really necessary for processing 1 raw file at a time or if lines are processed together, but as soon as
# written raw files cross over line numbers or many raw files are merged, it is best to make new out files so EV can use them properly.
merge_out_data = True
# start processing at a specified time- 
# either leave empty for process all, 
# or a list with one for date and time ['yyyymmdd','hhmmss']
#start_time = ['20230603', '081050']
start_time = []

# fill database with data files that have been procesed, 

# Make 'load_params' with database connection details if desired: user, schema, password, and dsn
# Set the survey id and ship id associated with these data files.
#  DATABASE NEEDS TO BE INITIALIZED FOR THIS SURVEY AND SHIP in the survey and frequency table
# Set the subsample number to insert data files for:

# Set load_params = {} if no loading desired
load_params = {'user':'avobase2', 'schema':'avobase2', 
                'password':'Pollock#2468','dsn':'afsc',
                'survey_id':202405, 'ship_id':134, 'ss_list':[1, 11]}

# Path to raw data to be processed- need two trailing slashes \\
# For now, within this directory, a new directory ('subsampled') will be created and sub directories for each iteration of subsample
#input_path='I:\\2012\\EBS_2012_Aldebaran\\'
input_path = 'H:\\AVO\\NWX_2024\\'


# Path to location where to create subsample directories- need two trailing slashes \\
# Leave empty if they should be created as subfolders in the input_path directory
#output_path='C:\\python_code\\AVO\\triwave_test\\new_corrected\\'
#output_path = 'C:\\temp\\temp\\'
output_path = 'H:\\AVO\\NWX_2024\\'

# How much data process at once (required):
# size_unit is the definition for how to count the amount of data.  
# This esstentially determines whether the loop for processing is over files or time.  Options include:
#       'file, in which the unit is one single file
#       'hour', in which the unit is one hour (this could be less than a file size-  need to handle this case at some point)
#       'day', in which the unit is one day
# size_number is the number of the 'units' to put together.
size_info = {'size_unit':'hour', 
                    'size_number':6}
                    
# Subsampling parameters (required):
# percent is percent of the dataset to subsample
# chunk_size is the number of contiguous pings to keep
# chunk_start is the starting ping for first subsample chunk: If this is greater than 100/percent_ss, it will be reduced to the integer between 1 and 100/percent_ss
# iterations is the number of subsample sets to produce: If this is greater than 100/percent, it will be set to 100/percent
# ss_params={} if no subsampling
ss_params = {'percent':5,
                    'chunk_size':50, 
                    'chunk_start':1, 
                    'iterations':20}

# Filter parameters:
# 'time_limit' can be the location+name of a csv file with definition for the time when data will be removed. 
#       This file needs four columns:  date start, date end, time to start including after (sunrise), time to stop including after (sunset).
#       OR it can be the keyword, 'use_solar_angle' to determine day or night on a ping by ping level for the date and lat/lon
#       The second item in the list is the time offset to apply to ping times before applying the time of day filter, default is 0
#
# 'speed_limit' is the minimum speed to keep data
#
# 'latlon_limit' is the path to a file that holds the coordinates of a bounding shape 
# and either 'in' or 'out' to designate whether to keep pings inside or outside the bounding shape.
#
# 'ringdown' or transmit pulse- parameters are:
# number of pings to take the median over- needs to be odd
# the difference in dB from that median to tag bad pings, 
# starting range in meters, 
# ending range in meters
# 
# 'bottom'- parameters are:
# type of bottom filter- 
# 'fixed' for a set threshold on vertical median bottom values
# or 'relative' for a threshold value on the difference between mean bottom value and running median of those values
# If 'fixed'
# minimum search range (m), 
# maximum search range (m), 
# the threshold in dB from the vertical median bottom values to tag bad pings,
# upper range from the detected bottom (m) for envelope to find median
# lower range from the detected bottom (m) for envelope to find median
# apply offset to match the bottom (in depth) to the pings (in range) using the transducer_depth.  E.g. Vesteraalen 2015.

# If 'relative'
# minimum search range (m), 
# maximum search range (m), 
# upper range from the detected bottom (m) for envelope to find median
# lower range from the detected bottom (m) for envelope to find median
# number of pings to take the median over- needs to be odd, 
# apply offset to match the bottom (in depth) to the pings (in range) using the transducer_depth.  E.g. Vesteraalen 2015.
# the difference in dB from that median to tag bad pings,


#filter_params={'time_limit':'C:\\python_code\\echolab\\saildrone-pre-processing\\data\\csv\\saildrone_south.csv', 'ringdown': [61, 0.1, 0, 3], 'bottom':[61, 15, 9999, 6, -30]}
#filter_params = {'latlon_limit': 'C:\\python_code\\AVO\\geo_test\\EBS_bounds.csv'}
filter_params = {'latlon_limit': ['G:\\AVO\Code\\pyAVO\\pyAVO2\\EBS_bounds.shp', 'in'],
                        'time_limit': ['use_solar_angle', 0],  
                        'speed_limit': 4, 
                        'ringdown': [61, 0.1, 0, 1], 
                        'bottom': ['fixed', 15, 9999, 0.5, 1.5, -40, True]}

# Extra operation (optional)
# It will look in here and perform anything requested
# Some options include:
# 'triwave_correct'- parameters are:
# start sample number, 0 indexed
# end sample number, 0 indexed
# 'bottom_detect'}
triwave_params = {'start_sample': 0, 
                            'end_sample':2}

# Set up parameters around tracking ping removal
# Determine how to count the number of pings removed compared to total pings
# 'statistics interval - This number specifies how many pings to compute over
# 'threshold to remove' - This specifies what percent of bad pings should cause a removal of the whole interval
pr_params = {'statistic_interval': 50, 
                        'threshold_to_remove': 15}


map_params = {'save': True, 'grids': 'G:\\AVO\Code\\pyAVO\\pyAVO2\\BT_grids.shp'}

#
# BEGIN PROCESSING CODE
#
# First record the parameters used in this analysis in the main output folder
def record_params(write_dict):
    f_name = output_path+'run_params_{:%d-%m-%Y-%H-%M-%S}.txt'.format(datetime.datetime.now())
    with open(f_name, 'w') as f:
        for key, value in write_dict.items():
            f.write('%s: %s\n' % (key, value))
param_dict = {}
for i in ('instrument', 'minimum_pings_to_write', 'write_orig', 'make_echogram', 'save_gps', 'primary_frequency', 'merge_out_data', 
            'start_time', 'load_params', 'input_path', 'output_path', 'size_info', 'ss_params', 'filter_params', 'triwave_params', 
            'pr_params', 'map_params'):
    param_dict[i] =locals()[i]
record_params(param_dict)

# Find raw files in path
files = glob.glob(input_path+'*.raw')
num_of_files = len(files)

# Find out files in path, if there are any.
out_files = None
if 'bottom' in filter_params:
    out_files = glob.glob(input_path+'*.out')

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

# Initialize the logger with processing meta data
if not ss_params or ss_params['percent']==100:
    logging.info('Subsampling will not be performed, as requested')
else:
    logging.info('Subsampling: {} percent, {} ping chunks, {} iterations starting with ping number {}'.format(ss_params['percent'], ss_params['chunk_size'], ss_params['iterations'], ss_params['chunk_start']))
logging.info('{} {}(s) will be processed at a time'.format(size_info['size_number'], size_info['size_unit']))

# Initialize process and merge objects for use later
# Processor is the main processing loop that does all the raw file subsampling/filtering/reporting/mapping/making echograms
processor = Process(instrument, primary_frequency, output_path,
                        minimum_pings_to_write, write_orig, make_echogram, save_gps, load_params,
                        pr_params, ss_params, triwave_params, filter_params, map_params)
# Merger is the merging of out (bottom) files together and renaming to match the processor output raw data
merger = Merge(load_params)

# Get bottom file (out) date times for easier searching later
if 'bottom' in filter_params:
    out_date_times = []
    for f in out_files:
        d_start=f.find('-D')+2
        f_date=f[d_start:d_start+8]
        t_start=f.find('-T')+2
        f_time=f[t_start:t_start+6]
        out_date_times.append(pd.to_datetime(f_date+'-'+f_time))
    out_ind = np.argsort(out_date_times)
    out_date_times = np.array(out_date_times)[out_ind]
    out_files = np.array(out_files)[out_ind]

# CASE 1 of processing: If file size info is dependent on a time unit:
# Compile dictionary of file names and start times, so indexing by hour/day will be easy,
# Then loop through size intervals specified
f_full_dates=[]
f_dates=[]
f_times=[]
ping_stats = {}
unit=size_info['size_unit']
num=size_info['size_number']
size_suffix = '-unit'+str(size_info['size_number'])+size_info['size_unit']+'.raw'
if unit in {'hour', 'day'}:
    file_dt=[]
    for f in files:
        d_start=f.find('-D')+2
        f_date=f[d_start:d_start+8]
        t_start=f.find('-T')+2
        f_time=f[t_start:t_start+6]
        f_full_dates.append(pd.to_datetime(f_date+'-'+f_time))
        f_dates.append(pd.to_datetime(f_date).date())
        f_times.append(pd.to_datetime(f_date+'-'+f_time).time())
    # Now create the timing grid to cyle through
    freq=str(num)+str(unit[0])
    if unit=='hour':
        if start_time:
            date_range=pd.date_range(pd.to_datetime(start_time[0]+'-'+start_time[1]),np.max(f_full_dates)+pd.to_timedelta(num, unit='h'), None, freq)
        else:
            date_range=pd.date_range(np.min(f_full_dates),np.max(f_full_dates)+pd.to_timedelta(num, unit='h'), None, freq)
    else:
        if start_time:
            date_range=pd.date_range(pd.to_datetime(start_time[0]).date(),np.max(f_dates),None,freq)
        else:
            date_range=pd.date_range(np.min(f_dates),np.max(f_dates),None,freq)
    is_first = True
    is_last = False
    for i, d in enumerate(date_range):
        cur_files=[]
        if d == date_range[-1]:
            is_last = True
        if unit=='hour':
            if i==0:
                last_date=d
            else:
                for ind, full_d in enumerate(f_full_dates):
                    if full_d>=last_date and full_d<d:
                        cur_files.append(files[ind])
                last_date=d
        else:
            for ind, date in enumerate(f_dates):
                if date==pd.to_datetime(d).date():
                    cur_files.append(files[ind])
        if cur_files!=[]:
            cur_files.sort()
            # Gather a list of bottom files associated with these raw files, if needed for filtering or merging
            if 'bottom' in filter_params or merge_out_data:
                cur_out_files = []
                if out_date_times.size>0:
                    for f in cur_files:
                        d_start=f.find('-D')+2
                        f_date=f[d_start:d_start+8]
                        t_start=f.find('-T')+2
                        f_time=f[t_start:t_start+6]
                        cur_date_time = pd.to_datetime(f_date+'-'+f_time)
                        out_file_ind = np.max(np.where(out_date_times <= cur_date_time))
                        cur_out_files.append(out_files[out_file_ind])
                    cur_out_files = np.unique(cur_out_files)
            # Do the main processing here
            val = processor.process(cur_files, size_suffix, mk_dirs=is_first, last_one=is_last, out_list=cur_out_files)
            # If the processing was successful and merging of out files is desired, do it here for the subsamples specified in the load params
            if val[1] and merge_out_data:
                # Merge bottom data and distribute into subsample folders specified in load params
                for iters in range(ss_params['iterations']):
                    cur_iter = int((iters+ss_params['chunk_start']-1)%(100/ss_params['percent']))
                    if cur_iter in load_params['ss_list']:
                        ss_str = str(cur_iter)
                        ss_line_prefix = 'L'+ss_str.zfill(4)+'-'
                        start_file = cur_files[0]
                        merge_name = output_path+'SS_'+ss_str+'\\'+ss_line_prefix+start_file[start_file.rfind('\\')+7:-4]+'.out'
                        merger.merge(in_files=cur_out_files, out_file_name=merge_name)
                        logging.info("Finished combining out data to file(s) {}".format(merge_name))
            is_first=False

# CASE 2 of processing: If file size info is not dependent on a time unit and is based on file unit
# Compile dictionary of file names and start times, so indexing by hour/day will be easy,
# Loop through the files on the interval specified
else:
    is_first = True
    is_last = False
    # Build an index to loop through the correct spacing of files
    for i in np.arange(0, num_of_files, size_info['size_number']):
        # If the last set of files is being processed, pass that into the processor, for different treatment
        if i == num_of_files-1:
            is_last = True
        cur_files = files[i:i+size_info['size_number']]
        # Gather a list of bottom files associated with these raw files, if needed for filtering or merging
        if 'bottom' in filter_params or merge_out_data:
            cur_out_files = []
            if out_date_times.size>0:
                for f in cur_files:
                    d_start=f.find('-D')+2
                    f_date=f[d_start:d_start+8]
                    t_start=f.find('-T')+2
                    f_time=f[t_start:t_start+6]
                    cur_date_time = pd.to_datetime(f_date+'-'+f_time)
                    out_file_ind = np.max(np.where(out_date_times <= cur_date_time))
                    cur_out_files.append(out_files[out_file_ind])
                cur_out_files = np.unique(cur_out_files)
        # Do the main processing here
        val = processor.process(cur_files, size_suffix, mk_dirs=is_first, last_one=is_last, out_list=cur_out_files)
        # If the processing was successful and merging of out files is desired, do it here for the subsamples specified in the load params
        if val[1] and merge_out_data:
            # Merge bottom data and distribute into subsample folders, load file name if desired
            for iters in range(ss_params['iterations']):
                cur_iter = int((iters+ss_params['chunk_start']-1)%(100/ss_params['percent']))
                if cur_iter in load_params['ss_list']:
                    ss_str = str(cur_iter)
                    ss_line_prefix = 'L'+ss_str.zfill(4)+'-'
                    start_file = cur_files[0]
                    merge_name = output_path+'SS_'+ss_str+'\\'+ss_line_prefix+start_file[start_file.rfind('\\')+7:-4]+'.out'
                    merger.merge(in_files = cur_out_files, out_file_name = merge_name)
                    logging.info("Finished combining out data to file(s) {}".format(merge_name))
        is_first = False
        
