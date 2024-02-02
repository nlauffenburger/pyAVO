# -*- coding: utf-8 -*-

import sys,  os, csv, logging
from echolab2.instruments import EK60,  EK80
from echolab2.plotting.matplotlib import echogram
from echolab2.processing import afsc_bot_detector
from pyAVO2.subsample import Subsample
from pyAVO2.triwave_correct import TriwaveCorrect
from pyAVO2.filter import Filter
from pyAVO2.map import Map
from pyAVO2 import avo_db
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure
import cartopy.io.shapereader as shpreader
import shapefile
import geopy.distance as gd

class Process():
    '''
    Contains methods for processing AVO data
    Organization of executing triwave correction, subsampling, 
    filtering, reporting, and mapping
    '''
    def __init__(self, instrument, primary_frequency, output_path,
                        minimum_pings_to_write, write_original, make_echogram, save_gps, load_params,
                        pr_params, ss_params, triwave_params, filter_params, map_params):
        '''
        Initializes Process class with parameters for processing
        '''
        # General set up parameters for processing
        self.instrument = instrument
        self.primary_frequency = primary_frequency
        self.output_path = output_path
        self.minimum_pings_to_write = minimum_pings_to_write
        self.write_original = write_original
        self.make_echogram = make_echogram
        self.save_gps = save_gps
        need_gps_data = False
        need_bottom_data = False

        # Subsampling set up parameters and initialize subsample object
        self.ss_params = ss_params
        if not ss_params:
            self.ss_params['iterations'] = 1
            self.ss_params['do_subsample'] = False
        else:
            self.ss_params['do_subsample'] = True
            self.subsampler = Subsample(ss_params['chunk_size'], ss_params['percent'])
            
        # Triwave correction set up parameters and initialize corrections object
        self.triwave_params = triwave_params
        if not triwave_params:
            self.triwave_params['do_triwave'] = False
        else:
            self.triwave_params['do_triwave'] = True
            self.triwave_correcter = TriwaveCorrect(triwave_params['start_sample'], triwave_params['end_sample'])
                
        # Filtering for time of day, speed, bottom and ringdown
        self.filter_params = filter_params
        N = len(filter_params)
        if not filter_params:
            do_filtering = False
        else:
            do_filtering = True
            if 'time_limit' in filter_params or 'speed_limit' in filter_params or 'latlon_limit' in filter_params:
                need_gps_data = True
            if 'bottom' in filter_params:
                need_bottom_data = True
            if 'latlon_limit' in filter_params:
                filter_params['latlon_limit'][0] = self.get_latlon_pairs(filter_params['latlon_limit'][0], 2)
            self.filterer = Filter(filter_params, pr_params=pr_params)
            self.ping_stats = pr_params
        
        # Apply these settings for our process to use when feeding the filterer
        self.filter_settings = {}
        self.filter_settings['number_of_filters'] = N
        self.filter_settings['do_filtering'] = do_filtering
        self.filter_settings['need_gps_data'] = need_gps_data
        
        # Mapping parameters on whether to make a map
        self.map_params = map_params
        if not map_params:
            self.map_params['make_map'] = False
        else:
            map_params['save_path'] = output_path+'maps\\'
            self.mapper = Map(map_params)
            self.map_params['make_map'] = True
            self.map_params['plot_region'] = True
            need_gps_data = True
            # Need to build in condition for checking here
            if self.map_params['plot_region']:
                self.map_params['region'] = filter_params['latlon_limit'][0]
            if self.map_params['grids']:
                self.map_params['grids'] = self.get_latlon_pairs(map_params['grids'], 4)
            self.all_latitudes = []
            self.all_longitudes = []
            self.all_labels = []
            self.all_labels_by_filtering = []
            self.gps_counter = 0
        
        # Set inital GPS data flag
        # Do not need to pass in GPS data unless there is a filter or file save requiring it
        if save_gps:
           need_gps_data = save_gps
        
        # Set up database object, if there will be loading of the data files table
        if not load_params:
            need_to_load = False
        if load_params:
            need_to_load = True
            self.db_manager = avo_db.Connection(user=load_params['user'], 
                password=load_params['password'], dsn=load_params['dsn'],
                                      schema=load_params['schema'])
            self.db_cursor = self.db_manager.cursor()
            self.load_params = {}
            self.load_params['survey_id'] = load_params['survey_id']
            self.load_params['ship_id'] = load_params['ship_id']
            self.load_params['ss_list'] = load_params['ss_list']
        
        # Finally set up processing setting parameters
        self.process_settings = {}
        self.process_settings['need_gps_data'] = need_gps_data
        self.process_settings['need_bottom_data'] = need_bottom_data
        self.process_settings['need_to_load'] = need_to_load
        
    def process(self, file_list, size_suffix, mk_dirs=True, last_one=False, out_list=None):
        '''
        Primary method to process data files
        
        '''

        # Create an instance of the EK instrument.
        # Use instrument parameter to initialize the proper object, either EK60 or EK80
        if self.instrument=='EK60':
            ek = EK60.EK60()
        elif self.instrument=='EK80':
            ek = EK80.EK80()
            
        print('Reading source file(s):')
        # Read in files from the file list.  pyecholab2 allows for providing multiple files
        # in a list to all be read into one raw_data object
        try:
            ek.read_raw(file_list, progress_callback=self.read_write_callback)
            # If there are issues with non-primary frequencies, use this following commented out line to only process the primary
            #ek.read_raw(file_list, progress_callback=self.read_write_callback, frequencies=[self.primary_frequency])
            logging.info("Finished successful reading raw data from file(s) {}".format(file_list))
        except:
            logging.error("There was a problem with reading raw data from files {}".format(file_list))
            return False,  False
        # Read in out files from the out file list
        if self.process_settings['need_bottom_data']:
            try:
                ek.read_bot(out_list, progress_callback=self.read_write_callback)
                logging.info("Finished successful reading out data from file(s) {}".format(out_list))
                self.process_settings['detect_bottom'] = False
            except:
                logging.error("There was a problem with reading out data from files {}, will detect bottom".format(out_list))
                # Here instead of failing completely, use custom bottom detection
                self.process_settings['detect_bottom'] = True
            
        # Find the first file with path in the list and find the base name without path attached
        start_file = file_list[0]
        start_file_base_name = start_file[start_file.rfind('\\')+7:]
        orig_line_prefix = start_file[start_file.rfind('\\')+1:start_file.rfind('\\')+6]
        
        # Do some channel organization and clean up here
        # Make sure 38 (primary, set at the beginning) is read first, 
        # so the subsampling index from 38 can be applied to other frequencies
        # In addition, there is some data quality issues with saildrone, where there is only one 'sector'
        # In this case, just remove the file that has the bad data and move on.
        channel_list = []
        for key, value  in ek.frequency_map.items():
            L = len(ek.raw_data[value[0]])
            if self.instrument == 'EK80':
                # Check to see if there is more than one data object for this channel ID
                # This will happen for saildrone and we need to get rid of the one with a single sector
                if L > 1:
                    for idx in range(0, L):
                        num_of_sectors = ek.raw_data[value[0]][idx].complex.shape[2]
                        if num_of_sectors < 3:
                            idx_to_remove = idx
                    ek.raw_data[value[0]].remove(ek.raw_data[value[0]][idx_to_remove])
                    # check to make sure the first file name is still in there
                    start_file = ek.raw_data[value[0]][0].configuration[0]['file_name']
            
            # If there are a list of raw data objects, there is probably something wrong- 
            # perhaps a setting was changed or there was an erroneous ping.
            # If there is an 'empty' raw_data object, just remove it.
            # If there are two non-empty raw_data objects or all empty raw_data objects, 
            # then skip this file, make a note and move on.
            skip_this_file = False
            if L > 1:
                idx_to_remove = []
                for idx in range(0, L):
                    if ek.raw_data[value[0]][idx].n_pings == 1 or ek.raw_data[value[0]][idx].power.size == 0:
                        idx_to_remove = np.append(idx_to_remove, idx)
                if len(idx_to_remove) == 0 or len(idx_to_remove) == L:
                    skip_this_file = True
                else:
                    for i in np.flip(idx_to_remove):
                        ek.raw_data[value[0]].remove(ek.raw_data[value[0]][int(i)])
            if skip_this_file:
                logging.error("There were two raw data objects for one frequency and could not determine the cause, so skipping {}".format(file_list))
                return False,  False
            
            # Now check to see if this  is the primary frequency to base index for others off of
            # If so, keep track and make sure primary is the first in the list
            if key == self.primary_frequency:
                channel_list.insert(0, value[0])
                channel_primary = value[0]
            else:
                channel_list.append(value[0])
        
        # Save whether triwave correction should be applied. 
        # It will be applied to the first iteration and then it does not need to be applied in the subsequent iterations.
        # Save the original state so that the processing class can be set to the original state at the end.
        wrote_a_raw_file = False
        tw_correct = self.triwave_params['do_triwave']
        for iters in range(self.ss_params['iterations']):
            # After performing all the operations, we need to know whether at least one channel will be empty
            logging.info('Begin processing iteration {} out of {}'.format(iters+1, self.ss_params['iterations']))
            minimum_pings = True
            # Set up for subsampling with directories
            if self.ss_params['do_subsample']:
                cur_iter = int((iters+self.ss_params['chunk_start']-1)%(100/self.ss_params['percent']))
                ss_str = str(cur_iter+1)
                ss_line_prefix = 'L'+ss_str.zfill(4)
                if mk_dirs:
                    try:
                        os.mkdir(self.output_path+'SS_'+ss_str)
                        logging.info('Successful creation of folder: {}'.format('SS_'+ss_str))
                    except: 
                        logging.info(self.output_path+'SS_'+ss_str+' already exists')
                out_dir = self.output_path+'SS_'+ss_str+'/'
                start_ping = cur_iter*self.ss_params['chunk_size']
            else:
                out_dir =  self.output_path
                cur_iter = 0
            # Create the empty raw index dictionary
            raw_index_array = {}
                    
            # first, iterate through the channels we have read (starting with 38)
            for channel in channel_list:
                # And then the data objects associated with each channel
                logging.info('Begin processing frequency channel {}'.format(channel))
                for data in ek.raw_data[channel]: 
                    # Perform triwave correction if desired for every channel
                    if self.triwave_params['do_triwave']:
                        if data.n_pings<1360:
                            logging.warning('Too few pings to triwave correct.')
                            logging.warning('Triwave correction was not performed, skipping this step...')
                        else:
                            data, fit_results, val = self.triwave_correcter.triwave_correct(data)
                            if not val:
                                logging.warning('Triwave correction was not performed, skipping this step...')
                            else:
                                logging.info('Triwave correction was performed successfully.')
                                val = self.write_csv_report('triwave_report', self.output_path, start_file_base_name[0:-4], data.frequency[0], None, fit_results)
                    
                    if channel==channel_primary:
                        # Build up boolean array with pings to keep
                        # Start with all true bool array for pings
                        idx_array=np.ones(data.n_pings, dtype=bool)

                        # Do initial processing to acquire GPS, bottom data or others
                        if iters == 0:
                            # Try to read in bottom data
                            if self.process_settings['need_bottom_data']:
                                if hasattr(data, 'detected_bottom'):
                                    bottom_data = data.get_bottom()
                                    if bottom_data.data is None or len(np.where(np.isnan(bottom_data.data))[0])==len(bottom_data.data):
                                        logging.info("There was a problem reading bottom data from {} file, will detect bottom".format(out_list))
                                        self.process_settings['detect_bottom'] = True
                                    else:
                                        logging.info("Successfully read bottom data from {}".format(out_list))
                                else:
                                    logging.info("There was a problem reading bottom data from {} file, will detect bottom".format(out_list))
                                    self.process_settings['detect_bottom'] = True
                                    bottom_data = []
                            else:
                                bottom_data = None
                            # If bottom data is not available, detect it
                            if self.process_settings['detect_bottom']:
                                bot_detector = afsc_bot_detector.afsc_bot_detector(search_min=15, backstep=35)
                                Sv_data = data.get_Sv()
#                                try:
                                bottom_data, _= bot_detector.detect(Sv_data) 
                                logging.info("Successfully detected bottom data for {}".format(file_list))
#                                except:
#                                    logging.info("Error in detecting bottom data for {}".format(file_list))
                            # Fill nans in bottom with closest
                            nan_inds = np.argwhere(np.isnan(bottom_data.data))
                            while np.any(nan_inds):
                                bottom_data.data[nan_inds] = bottom_data.data[nan_inds-1]
                                nan_inds = np.argwhere(np.isnan(bottom_data.data))

                            # Get GPS data, including position and speed
                            if self.process_settings['need_gps_data']:
                                blank, gps_data = ek.nmea_data.interpolate(data, 'position')
                                # Find any erroneous GPS fixes and set them to nan
                                gps_data = self.mark_bad_gps_data(gps_data)
                                no_gps = np.all(np.isnan(gps_data['latitude'])) or np.all(np.isnan(gps_data['longitude']))
                                if no_gps:
                                    logging.warning('There are no GPS data available.')
                                fields, speeds = ek.nmea_data.interpolate(data, 'speed')
                                speed_data = speeds[fields[0]]
                                no_speed = np.any(np.isnan(speed_data))
                                if no_speed:
                                    logging.info('There are no speed data available.')
                                    if no_gps:
                                        logging.warning('There are no GPS data to compute speeds. No speeds will be used.')
                                    else:
                                        speed_data,  val = self.compute_speed_from_gps(speed_data, gps_data)
                                        if val:
                                            logging.info('Speed data successfully computed from GPS data')
                                        else:
                                            logging.info('Unable to find missing speed data from GPS. Some speeds may still be missing.')
                                gps_data['speed'] = speed_data

                        # Subsample
                        if self.ss_params['do_subsample']:
                            idx_ss_array, ss_starts, ss_stops, val = self.subsampler.subsample(data.ping_time.shape[0], start_ping)
                            if not val:
                                logging.warning('Subsampling was not performed, skipping this step...')
                            else:
                                logging.info('Subsamping was performed successfully on primary frequency.')
                                if iters ==0:
                                    val = self.write_csv_report('subsample_report', out_dir, ss_line_prefix+'-'+start_file_base_name[0:-4], cur_iter+1, data.ping_time, (ss_starts, ss_stops), config=data.configuration)
                                    first_config = data.configuration.copy()
                                else:
                                    val = self.write_csv_report('subsample_report', out_dir, ss_line_prefix+'-'+start_file_base_name[0:-4], cur_iter+1, data.ping_time, (ss_starts, ss_stops), config=first_config)
                                    
                        
                        # Filter for day, speed, and for dropouts (bottom and ringdown filters)
                        if self.filter_settings['do_filtering']:
                            if iters == 0:
                                if self.filter_settings['need_gps_data']:
                                    if 'bottom' in self.filter_params:
                                        idx_filt_array, val = self.filterer.do_all_filtering(data, gps_data=gps_data, bottom_data=bottom_data.data)
                                    else:
                                        idx_filt_array, val = self.filterer.do_all_filtering(data, gps_data=gps_data)
                                else:
                                    if 'bottom' in self.filter_params:
                                        idx_filt_array, val  = self.filterer.do_all_filtering(data, bottom_data=bottom_data.data)
                                    else:
                                        idx_filt_array, val  = self.filterer.do_all_filtering(data)
                                
                                # Save filtered array for use in following iterations, if needed
                                if self.ss_params['iterations'] > 1:
                                    idx_filt_array_saved = idx_filt_array
                                
                                # Remove intervals with dropouts above threshold provided
                                idx_ss_array, self.ping_stats['data'], self.ping_stats['tracking'] = self.filterer.remove_intervals(idx_ss_array=idx_ss_array)
                                
                                if not val:
                                    logging.warning('None of the filtering was successfully performed, skipped all')
                                else:
                                    idx_array = np.logical_and(idx_filt_array, idx_ss_array)
                                    logging.info('{} out of {} filters were successfully applied'.format(val, self.filter_settings['number_of_filters']))
                                    
                            else:
                               logging.info('Filtering from first iteration was successfully applied to following iteration')
                               idx_ss_array, self.ping_stats['data'], self.ping_stats['tracking'] = self.filterer.remove_intervals(idx_ss_array)
                               idx_array = np.logical_and(idx_filt_array_saved, idx_ss_array)
                        else:
                            idx_array = idx_ss_array
                            
                        # Save subsampling array and data from primary (typically 38 kHz)
                        idx_array_primary = idx_array.copy()
                        data_primary = data.copy()
                        
                        # Save echogram image of primary frequency data in first iteration
                        if self.make_echogram and iters == 0:
                            if mk_dirs:
                                try:
                                    os.mkdir(self.output_path+'echograms')
                                    logging.info('Successful creation of folder: echograms')
                                except: 
                                    logging.info(self.output_path+'echograms already exists')
                            Sv = data.get_Sv()
                            plot_data = Sv.copy()
                            fig = figure(figsize=(18, 4.8))
                            eg = echogram.Echogram(fig, plot_data, threshold=[-70, -34])
                            # Plot bottom if has been loaded or detected- use different color depending on which
                            if bottom_data is not None:
                                if self.process_settings['detect_bottom']:
                                    eg.plot_line(bottom_data, linewidth=0.05, color='k', linestyle='solid')
                                else:
                                    eg.plot_line(bottom_data, linewidth=0.05, color='g', linestyle='solid')
                            fig.savefig(self.output_path+'echograms\\'+start_file_base_name[0:-4], dpi=1200)
                            plt.close(fig)
                    else:
                        # If this is not the primary frequency, match pings to it
                        # Match pings to primary, which has been subampled and filtered
                        data.match_pings(data_primary)
                        logging.info('Subsampling and filtering from primary frequency was matched to secondary frequency.')
                        # Use subsampled and filtered array from primary (typically 38 kHz)
                        idx_array = idx_array_primary

                    # Set the index array for this raw_data object
                    raw_index_array[data] = idx_array
                    
                    # Determine whether there are enough pings left over after subsampling and filtering to write a new file
                    n_good_pings=len(np.where(idx_array)[0])
                    if n_good_pings<self.minimum_pings_to_write:
                        minimum_pings=False
                    
                    # Apply the configuration of the first ping to all the pings for consistency and to not violate any rules
                    data.configuration[:] = data.configuration[0]
                    
            if minimum_pings:
                # Write the new file.
                print('Writing processed file(s):')
                # Designate more specific file name for subsampling.
                # If subsampling wasn't performed, then just use suffix with file grouping ('size') information
                if self.ss_params['do_subsample']:
                    file_suffix = '-ping'+str(start_ping).zfill(5)+'_run'+str(self.ss_params['chunk_size'])+'-stride'+str(self.ss_params['percent'])+size_suffix
                else:
                    file_suffix = size_suffix
                # Make dictionary that raw writer needs to write out the proper name
                out_file_name = {orig_line_prefix+'-'+start_file_base_name:out_dir+ss_line_prefix+'-'+start_file_base_name[0:-4]+file_suffix}
                # Write raw file
                ek.write_raw(out_file_name, raw_index_array=raw_index_array, overwrite=True, progress_callback=self.read_write_callback)
                logging.info("Finished writing raw data to file(s) {}".format(out_file_name))
                wrote_a_raw_file = True
                if cur_iter+1 in self.load_params['ss_list']:
                    # Need to check if this data file is already in there
                    val = self.db_cursor.get_datafile(self.load_params['ship_id'], self.load_params['survey_id'],
                        ss_line_prefix+'-'+start_file_base_name[0:-4]+file_suffix)
                    if not val:
                        # If it isn't in the database already, insert it
                        self.db_cursor.insert_datafile(self.load_params['ship_id'], self.load_params['survey_id'], return_id=False,
                            line=int(cur_iter+1), file_name=ss_line_prefix+'-'+start_file_base_name[0:-4]+file_suffix,
                            start_time=pd.Timestamp(data.ping_time[idx_array_primary][0]),
                            end_time=pd.Timestamp(data.ping_time[idx_array_primary][-1]),
                            n_pings=int(sum(idx_array_primary)),
                            clock_adj=0,
                            mean_skew=0,
                            stddev_skew=0,
                            status=avo_db.StatusCodes.UNCHECKED)
                            
                        logging.info("Finished inserting data file {} info to data_files table".format(ss_line_prefix+'-'+start_file_base_name[0:-4]+file_suffix))
                    else:
                        logging.info("Data file {} is already in the data files table".format(ss_line_prefix+'-'+start_file_base_name[0:-4]+file_suffix))
                        
                
                
            else:
                logging.info("Did not write raw data to file, number of pings left did not exceed minimum pings")
            
            # If it is desired to save an un-subsampled and un-filtered file 
            # that has the file grouping ('size') for referenced, do it here.
            if self.write_original and iters == 0:
                ocrf_name = 'original_compiled_raw_files'
                if mk_dirs:
                    try:
                        os.mkdir(self.output_path+ocrf_name)
                        logging.info('Successful creation of folder: '+ ocrf_name)
                    except: 
                        logging.info(self.output_path+ocrf_name+' already exists')
                file_suffix = '-no_ss_no_filtering'+size_suffix
                out_file_name = {start_file_base_name:self.output_path+ocrf_name+'\\'+start_file_base_name[0:-4]+file_suffix}
                ek.write_raw(out_file_name, overwrite=True, progress_callback=self.read_write_callback)
                logging.info("Finished writing original raw data to file(s) {}".format(out_file_name))
            
            logging.info('\n FINISHED ITERATION')
            
            # Second time around, data does not need to be triwave corrected:
            self.triwave_params['do_triwave'] = False
            # Save reporting csv files:
            if self.ss_params['do_subsample']:
                val = self.write_csv_report('filter_report', out_dir, ss_line_prefix+'-'+start_file_base_name[0:-4], cur_iter+1, data.ping_time, self.ping_stats)
            else:
                val = self.write_csv_report('filter_report', out_dir, start_file_base_name[0:-4], 1, data.ping_time, self.ping_stats)
                
        if self.save_gps:
            temp = np.zeros(len(idx_array))
            temp[idx_array] = 1
            gps_data['filter label'] = temp
            gps_data['file label'] = np.ones(len(gps_data['latitude']))*self.gps_counter
            val = self.write_csv_report('gps_report', self.output_path, start_file_base_name[0:-4], None, data.ping_time, gps_data)
            self.gps_counter += 1
            
        if self.map_params['make_map'] and last_one:
            try:
                os.mkdir(self.output_path+'maps')
                logging.info('Successful creation of folder: maps')
            except: 
                logging.info(self.output_path+'maps already exists')
            
            # Read data from gps report file
            all_latitudes = []
            all_longitudes = []
            all_labels = []
            all_labels_by_filtering = []
            all_labels_speed = []
            all_labels_hours = []
            with open(self.output_path+'gps_report.csv') as csvfile:
                csv_reader = csv.reader(csvfile, delimiter=',')
                line_count = 0
                for row in csv_reader:
                    if line_count>0:
                        all_labels_hours.append(int(row[1][11:13]))
                        all_latitudes.append(float(row[2]))
                        all_longitudes.append(float(row[3]))
                        all_labels_speed.append(np.floor(float(row[4])))
                        all_labels.append(float(row[5]))
                        all_labels_by_filtering.append(float(row[6]))
                    line_count+= 1
            self.mapper.draw_map(np.array(all_latitudes), np.array(all_longitudes), labels=all_labels, border=self.map_params['region'], file_name='by_file', grids=self.map_params['grids'])
            self.mapper.draw_map(np.array(all_latitudes), np.array(all_longitudes), labels=all_labels_by_filtering, border=self.map_params['region'], file_name='filtering', grids=self.map_params['grids'])
            self.mapper.draw_map(np.array(all_latitudes), np.array(all_longitudes), labels=all_labels_speed, border=self.map_params['region'], file_name='speed', grids=self.map_params['grids'], legend=True)
            self.mapper.draw_map(np.array(all_latitudes), np.array(all_longitudes), labels=all_labels_hours, border=self.map_params['region'], file_name='hours', grids=self.map_params['grids'], legend=True)
                
        logging.info('\n \n FINISHED FILE \n')
        
        # Set value of triwave correct back to original state for processor object
        # This was changed for 2+ iterations because correction was already applied to data object for all frequencies
        self.triwave_params['do_triwave'] = tw_correct
        
        self.db_manager.commit()
        return True, wrote_a_raw_file
    
    def mark_bad_gps_data(self, gps_data):
        st_lat = gps_data['latitude'][:-1]
        st_lon = gps_data['longitude'][:-1]
        end_lat = gps_data['latitude'][1:]
        end_lon = gps_data['longitude'][1:]
        count = 1
        for lat1, lon1, lat2, lon2 in zip(st_lat, st_lon, end_lat, end_lon):
            if not np.any(np.isnan((lat1, lon1, lat2, lon2))):
                if gd.distance((lat1, lon1), (lat2, lon2)).km > 0.1:
                    gps_data['latitude'][count-1:count] = np.nan
                    gps_data['longitude'][count-1:count] = np.nan
            count += 1
        
        return gps_data
    
    def compute_speed_from_gps(self, speed_data, gps_data):
        st_lat = gps_data['latitude'][:-1]
        st_lon = gps_data['longitude'][:-1]
        end_lat = gps_data['latitude'][1:]
        end_lon = gps_data['longitude'][1:]
        time_diff = gps_data['ping_time'][1:] - gps_data['ping_time'][:-1]
        val = False
        count = 1
        for lat1, lon1, lat2, lon2, tdiff, sp in zip(st_lat, st_lon, end_lat, end_lon, time_diff, speed_data[1:]):
            if np.isnan(sp):
                if not np.any(np.isnan((lat1, lon1, lat2, lon2))):
                    temp_dist = gd.distance((lat1, lon1), (lat2, lon2)).km
                    temp_sp = 3600 * 0.539957 * temp_dist / tdiff.tolist().total_seconds()
                    speed_data[count] = temp_sp
                    if not val:
                        val = True
            count += 1
            
        return speed_data,  val
    
    
    def get_latlon_pairs(self, infile, pair_number):
        pairs = []
        if infile[-3:] == 'csv':
            # Unpack data in csv file to get pairs of points
            with open(infile, 'r', newline='') as f:
                data_reader=csv.reader(f, delimiter=',')
                next(data_reader, None) # skip header
                for row in data_reader:
                    if pair_number == 2:
                        pairs.append([float(row[1]), float(row[0])])
                    elif pair_number == 4:
                        pairs.append([float(row[1]), float(row[0]), float(row[3]), float(row[2])])
        elif infile[-3:] == 'shp':
            if pair_number == 2:
                polygon = shapefile.Reader(infile)
                sh = polygon.shape()
                for point in sh.points:
                    pairs.append([float(point[0]), float(point[1])])
            elif pair_number == 4:
                reader = shpreader.Reader(infile)
                grids = reader.records()
                for g in grids:
                    point = g.bounds
                    pairs.append([(float(point[0]), float(point[1])), 
                                            (float(point[0]), float(point[3])),
                                            (float(point[2]), float(point[3])),
                                            (float(point[2]), float(point[1])),
                                            (float(point[0]), float(point[1]))])
                
        return pairs
    
    
    def write_csv_report(self, file_type, out_dir, start_file_base_name, cur_iter, ping_times, params, config=None):
        '''
        Method to add to csv report with data from this file:
        Either add to a file to keep track of which sections are subsampled
        Or add to a file with filtering statistics
        
        :param file_type: description of which type of report to generate
        :type file_type: str
        
        :param ping_times: either a list of times for pings for reporting
        :type ping_times: array(datetime64) 
        
        :param params: list of data to enter into report
        :type params: array or list of arrays
        
        :optional param config: configuration object from data structure
        :optional type config: dictionary of configuration by ping
        
        '''
        
        if file_type == 'subsample_report':
            file_name = out_dir+file_type+'-SS{}.csv'.format(cur_iter)
            
            # Make list of file names with the start/end ping index for each
            orig_file_names = []
            ping_range_start = []
            ping_range_end = []
            for ping in config:
                if ping['file_name'] not in orig_file_names:
                    orig_file_names.append(ping['file_name'])
                    if ping_range_start == []:
                        ping_range_start.append(0)
                    else:
                        ping_range_start.append(ping_range_end[-1]+1)
                    ping_range_end.append(ping['end_ping']-1)
            
            if not os.path.exists(file_name):
                with open(file_name, 'a', newline='') as csvfile:
                    headers = ['output file name', 'output file start ping', 'output file end ping', 'original file name for start ping', 'start ping', 'start ping time', 
                                        'original file name for end ping', 'end ping', 'end ping time']
                    csvwriter = csv.writer(csvfile, delimiter=',')
                    csvwriter.writerow(headers)
                    
            with open(file_name, 'a', newline='') as csvfile:
                csvwriter = csv.writer(csvfile, delimiter=',')
                for ss in np.transpose(params):
                    ind_orf_st = np.argwhere(np.logical_and(ss[0]>=ping_range_start, ss[0]<=ping_range_end))[0][0]
                    ind_orf_end = np.argwhere(np.logical_and(ss[1]>=ping_range_start, ss[1]<=ping_range_end))[0][0]
                    data_to_write = [start_file_base_name, ss[0], ss[1], 
                                                orig_file_names[ind_orf_st], ss[0]-ping_range_start[ind_orf_st], ping_times[ss[0]],  
                                                orig_file_names[ind_orf_end], ss[1]-ping_range_start[ind_orf_end], ping_times[ss[1]]]
                    start_file_base_name = ''
                    csvwriter.writerow(data_to_write)
        
        if file_type == 'triwave_report':
            file_name = out_dir+file_type+'.csv'
            if not os.path.exists(file_name):
                with open(file_name, 'a', newline='') as csvfile:
                    headers = ['file name', 'frequency', 'r squared', 'amplitude offset', 'amplitude', 'period offset']
                    csvwriter = csv.writer(csvfile, delimiter=',')
                    csvwriter.writerow(headers)
            
            with open(file_name, 'a', newline='') as csvfile:
                data_to_write = [start_file_base_name, cur_iter, params['r_squared'], params['amplitude_offset'], params['amplitude'], params['period_offset']]
                csvwriter = csv.writer(csvfile, delimiter=',')
                csvwriter.writerow(data_to_write)
        
        if file_type == 'gps_report':
            file_name = out_dir+file_type+'.csv'
            
            if not os.path.exists(file_name):
                with open(file_name, 'a', newline='') as csvfile:
                    headers = ['file name', 'ping time', 'latitude', 'longitude', 'speed', 'file label', 'filter label']
                    csvwriter = csv.writer(csvfile, delimiter=',')
                    csvwriter.writerow(headers)
            
            with open(file_name, 'a', newline='') as csvfile:
                csvwriter = csv.writer(csvfile, delimiter=',')
                count = 0
                for p, lat, lon, sp, val1, val2 in zip(ping_times, params['latitude'], params['longitude'], params['speed'], params['file label'], params['filter label']):
                    if count == 0:
                        f_name = start_file_base_name
                    else:
                        f_name = ''
                    data_to_write = [f_name, p, lat, lon, sp, val1, val2]
                    csvwriter.writerow(data_to_write)
                    count += 1 
        
        if file_type == 'filter_report':
            file_name = out_dir+file_type+'-SS{}.csv'.format(cur_iter)
            if not os.path.exists(file_name):
                with open(file_name, 'a', newline='') as csvfile:
                    headers = ['file name', 'start ping', 'start ping time', 'end ping', 'end ping time', 
                                        'filter name',  'removed pings', 'total pings', 'percent removed',  
                                        'full file statistic?', 'file removed?',  'reason', 
                                        'interval statistic?', 'interval removed?', 'reason']
                    csvwriter = csv.writer(csvfile, delimiter=',')
                    csvwriter.writerow(headers)
            
            with open(file_name, 'a', newline='') as csvfile:
                
                for filt, vals in params['data'].items():
                    if filt == 'bottom' or filt == 'ringdown':
                        csvwriter = csv.writer(csvfile, delimiter=',')
                        count = 0
                        for v in zip(vals[0], vals[1], vals[2], vals[3], vals[4]):
                            if not np.isnan(v[0]):
                                data_to_write = [start_file_base_name, v[0], ping_times[int(v[0])], v[1], ping_times[int(v[1])], 
                                                    filt, v[2], v[3], v[4], '', '', '', 'Y', params['tracking']['interval_removed'][count], params['tracking']['interval_reason'][count]]
                            else:
                                data_to_write = [start_file_base_name, 'Err', 'Err', 'Err', 'Err', filt, 'Err', 'Err', 'Err', '', '', '', 'Y', params['tracking']['interval_removed'][count], params['tracking']['interval_reason'][count]]
                            csvwriter.writerow(data_to_write)
                            count += 1
                    
                    else:
                        if not np.isnan(vals[0]):
                            data_to_write = [start_file_base_name, vals[0], ping_times[vals[0]], vals[1], ping_times[vals[1]-1], 
                                                    filt, vals[2], vals[3], vals[4], 'Y', params['tracking']['file_removed'], params['tracking']['file_reason']]
                        else:
                            data_to_write = [start_file_base_name, 'Err', 'Err', 'Err', 'Err', filt, 'Err', 'Err', 'Err', 'Y', params['tracking']['file_removed'], params['tracking']['file_reason']]
                        
                        csvwriter = csv.writer(csvfile, delimiter=',')
                        csvwriter.writerow(data_to_write)
                    

                # insert a blank line for easy viewing
                csvwriter = csv.writer(csvfile, delimiter=',')
                csvwriter.writerow('')
    
    def read_write_callback(self, filename, cumulative_pct, cumulative_bytes, userref):
        '''
        read_write_callback is a simple example of using the progress_callback
        functionality of the EK60.read_raw and EK60.write_raw methods.
        '''

        if cumulative_pct > 100:
            return

        if cumulative_pct == 0:
            sys.stdout.write(filename)

        if cumulative_pct % 4:
            sys.stdout.write('.')

        if cumulative_pct == 100:
            sys.stdout.write('  done!\n')
    
