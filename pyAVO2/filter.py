
import logging, csv
import pandas as pd
import numpy as np
from astral import LocationInfo
from astral.sun import sun
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from datetime import timedelta

class Filter():
    '''
    Class for filtering a data by vessel speed, time of day, geographic bounds, or dropouts (bottom & ringdown)
    In addition to filtering, class gives option to track ping statistics and remove marked intervals
    '''

    def __init__(self, filter_params, pr_params=None):
        '''
        Initialize filter parameters
        
        :param filter_params: list of filter names and parameters associated with each filtering step
        :type chunk_size: dict with key as filter names
        Must be one of the following: 'time_limit, 'speed_limit', 'latlon_limit', 'bottom', 'ringdown'
        
        '''
        self.filter_params = filter_params
        self.pr_params = pr_params
        self.filtered_arrays = {}
        
    def do_all_filtering(self, data, gps_data=None, bottom_data=None):
        '''
        Method to perform all the filtering that is specified by the filter params dictionary
        Will go through each filter and call appropriate method
        
        :param data: raw data object, which must contain raw power
        :type data: raw_data object derived from pyecholab2 raw_read method
        
        :param gps_data: intepolated latitude, longitude, and speed to ping data times
        :type gps_data: dict with arrays of length data.n_pings
        
        :param bottom_data: interpolated bottoms to ping data times
        :type bottom_data: array of length data.n_pings
        
        :returns idx_array: boolean array with True for pings to keep after all filters applied
        :returns int for number of successful filters applied
        '''
        
        idx_array = np.ones(data.n_pings, dtype=bool)
        # Keep track of success for all filter, start with 0  
        total_val = 0
        for filt, vals in self.filter_params.items():
            # Choose between filter names to select the right method to call
            if filt == 'time_limit':
                if len(vals)>2:
                    idx_filt_array, val = self.filter_by_time(data, vals, gps_data=gps_data)
                if len(vals)==2:
                    idx_filt_array, val = self.filter_by_time(data, vals[0], gps_data=gps_data, time_shift = vals[1])
            elif filt == 'speed_limit':
                idx_filt_array, val = self.filter_by_speed(vals, gps_data)
            elif filt == 'latlon_limit':
                idx_filt_array, val = self.filter_by_latlon(vals, gps_data)
            elif filt == 'bottom':
                idx_filt_array, val = self.bottom_filter(data, vals, bottom_data=bottom_data)
            elif filt == 'ringdown':
                idx_filt_array, val = self.ringdown_filter(data, vals)
            else:
                val = False
                logging.warning('Filter name, {}, not an available filter'.format(filt))
            
            if not val:
                # Save filtered arrays for use again in computing ping statistics.  
                self.filtered_arrays[filt] = None
                logging.warning('Error with filter {}.  Skipping this one...'.format(filt))
            else:
                # Save filtered arrays for use again in computing ping statistics.  
                self.filtered_arrays[filt] = idx_filt_array
                # Combine this filter with all previous.  Any False gets carried through with AND
                idx_array = np.logical_and(idx_array, idx_filt_array)
                logging.info('Filter {} was sucessfully applied'.format(filt))
                        
            # If a single one is True, consider it a success- 
            # This will indicate that nothing worked, or at least one did.
            total_val = total_val + np.int(val)

        return idx_array, total_val
        
        
    def filter_by_time(self, data, vals, gps_data=None, time_zone='UTC', time_shift=0):
        '''
        Method to filter by time:  Remove data before sunrise and after sunset
        Either uses a csv file for fixed sunrise/sunset times by date range
        OR finds the sunrise/sunset times from latitude, longitude and date of data
        
        :param data: raw data object, which must contain raw power
        :type data: raw_data object derived from pyecholab2 raw_read method
        
        :param vals: Either a csv file path with start and stop times by date range for sunset/sunrise
                            OR 'use_solar_angle'- uses lat/lon & date to find solar angle- sunrise & sunset
        :type vals: str
        
        :optional param gps_data: intepolated latitude and longitude to ping data times
        :type gps_data: dict with arrays of length data.n_pings
        
        :optional time_zone: time zone for computing the time of day/solar angle.  Default is 'UTC'
        :type: time_zone: str
        
        : optional time_shift: time shift (in hours) for shifting the ping time before finding time of day/solar angle
        : type: float
        
        :returns idx_array: boolean array with True for pings to keep
        :returns boolean for sucess of filter
        
        '''
        data_time=data.ping_time
        time_delta = timedelta(hours=time_shift)
        sunrise=[]
        sunset=[]
        if vals == 'use_solar_angle':
            # Find sunrise and sunset for UTC at the location for these data
            cur_lat = np.nanmean(gps_data['latitude'])
            cur_lon = np.nanmean(gps_data['longitude'])
            if np.isnan(cur_lat) or np.isnan(cur_lon):
                logging.warning('No latitude or longitude was found in gps data for using solar angle')
                return False, False
            # Use the date of the first ping to determine sunrise & sunset
            # Most the data COULD be on the following day, but the change
            # in sunrise & sunset from one day to the next is negligible.
            cur_date = (pd.to_datetime(data_time[0])+time_delta).date()
            loc = LocationInfo('Current', 'EBS', time_zone, cur_lat, cur_lon)
            try:
                sun_data = sun(loc.observer, date=cur_date, tzinfo=loc.timezone, dawn_dusk_depression=2)
            except:
                # The sun never went below the depression specified, so set the array to all true
                logging.warning('Sun never went down to specified depression, continuing without daytime filter applied.')
                idx_array = np.full((len(data_time),1),True)
                return idx_array,  True
            sunrise = pd.to_datetime(sun_data['sunrise']).time()
            sunset = pd.to_datetime(sun_data['sunset']).time()
            # Get the sunset for the same day, earlier
            if pd.to_datetime(sun_data['sunset']).date()>cur_date:
                cur_date = cur_date-timedelta(days=1)
                sun_data = sun(loc.observer, date=cur_date, dawn_dusk_depression=2)
                sunset = pd.to_datetime(sun_data['sunset']).time()

        else:
            # Get the day (sunrise=start_time) & night (sunset=end_time) limits for this file
            with open(vals, 'r', newline='') as f:
                data_reader=csv.reader(f, delimiter=',')
                next(data_reader, None) # skip header
                for row in data_reader:
                    # Just look at the first time in the file to see if it is inside bounds
                    if data_time[0]>pd.to_datetime(row[0]) and data_time[0]<pd.to_datetime(row[1]):
                        sunrise=pd.to_datetime(row[2]).time()
                        sunset=pd.to_datetime(row[3]).time()
            if sunrise == []:
                logging.warning('No sunrise/sunset was found from data times in dates provided by CSV file')
                return False, False

        # Need to handle two cases because logical for index array changes depending on whether sunrise is before or after the sunset
        time_array=(pd.to_datetime(data_time)+time_delta).time
        if sunrise < sunset:
            idx_array=np.logical_and(time_array>sunrise,  time_array<sunset)
        else:
            idx_array=np.logical_or(time_array>sunrise,  time_array<sunset)
        return idx_array, True
        
    def filter_by_speed(self, vals, gps_data):
        '''
        Method to filter by speed (knots): Remove data below input threshold
        
        :param vals: a threshold of speed (knots), below which data should be removed 
        :type vals: int
        
        :param gps_data: intepolated latitude and longitude to ping data times
        :type gps_data: dict with arrays of length data.n_pings
        
        :returns idx_array: boolean array with True for pings to keep
        :returns boolean for sucess of filter
        '''
        
        # First check to make sure there is speed data
        if len(np.argwhere(np.logical_not(np.isnan(gps_data['speed'])))) == 0:
            logging.warning('There are no speed data for filtering')
            return False, False
        idx_array = gps_data['speed'] >= vals
        return idx_array, True
        
    def filter_by_latlon(self, vals, gps_data):
        '''
        Method to filter by location: Remove data outside region specified
        
        :param vals: bounding region lat/lon pairs
        :type vals: str
        
        :param gps_data: intepolated latitude and longitude to ping data times
        :type gps_data: dict with arrays of length data.n_pings
        
        :returns idx_array: boolean array with True for pings to keep (inside region)
        :returns boolean for sucess of filter
        '''
        # Get the latitude and longitude for all the vertices
        idx_array = []
        pairs = vals[0]
        polygon = Polygon(pairs)
        if len(np.argwhere(np.logical_not(np.isnan(gps_data['latitude'])))) == 0:
            logging.warning('There are no latitude/longitude data for filtering')
            return False, False
        else:
            for cur_lat, cur_lon in zip(gps_data['latitude'], gps_data['longitude']):
                if vals[1]=='in':
                    idx_array.append(polygon.contains(Point(cur_lon, cur_lat)))
                else:
                    idx_array.append(not polygon.contains(Point(cur_lon, cur_lat)))
        
        return np.array(idx_array), True
        
    def bottom_filter(self, data, vals, bottom_data):
        '''
        Remove pings with Sv that varies from the running median of Sv mean (computed in linear)
        in a specified range of max Sv (near the bottom).
        
        :param data: raw data object, which must contain raw power
        :type data: raw_data object derived from pyecholab2 raw_read method
        
        :param vals: array of values for ringdown filtering- [ ] 
        :type vals: list(str,int) of length 6 or 7
        
        :returns idx_array: boolean array with True for pings to keep after subsampling
        :returns boolean for sucess of filter
        '''
        # Check number of filtering params
        if len(vals) != 7 and len(vals) != 8:
            logging.warning('Incorrect number input values for bottom filtering')
            return False, False
        
        # If there are no bottom data, then cannot perform this filter
        if bottom_data == [] or bottom_data is None:
            logging.warning('No bottom data available for bottom filtering')
            return False,  False
        
        type = vals[0]
        
        # Find Sv
        Sv = data.get_Sv()
        range_ind = np.logical_and(Sv.range>vals[1], Sv.range<vals[2])
        mean_bottoms = []
        top_line = []
        bottom_line = []
        for ping, bot, t_depth in zip(Sv, bottom_data, Sv.transducer_offset):
            if not np.isnan(np.nanmax(ping[range_ind])):
                #max_Sv=np.nanmax(ping[range_ind])
                #max_ind=np.where(ping==max_Sv)
                if vals[6]:
                        bot = bot-t_depth
                env_upper = bot-vals[3]
                env_lower = bot+vals[4]
                top_line.append(env_upper)
                bottom_line.append(env_lower)
                env_ind = np.logical_and(Sv.range >= env_upper, Sv.range<=env_lower)
                if type == 'fixed':
                    mean_bottoms = np.append(mean_bottoms, 10*np.log10(np.median(10**(ping[env_ind]/10))))
                elif type == 'relative':
                    mean_bottoms = np.append(mean_bottoms, 10*np.log10(np.median(10**(ping[env_ind]/10))))
            else:
                mean_bottoms=np.append(mean_bottoms, np.nan)
       
        if type == 'fixed':
            bool_bottom = mean_bottoms>vals[5]
        elif type == 'relative':
            medians = self.get_running_median(mean_bottoms, vals[5])
            bool_bottom = mean_bottoms>(medians-vals[7])
        
        return bool_bottom, True
        
        
    def ringdown_filter(self, data, vals):
        '''
        Remove pings with Sv that varies from the running median of Sv mean (computed in linear)
        in a specified range from transducer.
        
        :param data: raw data object, which must contain raw power
        :type data: raw_data object derived from pyecholab2 raw_read method
        
        :param vals: array of values for ringdown filtering- [ ] 
        :type vals: array(int) of length 4
        
        :returns idx_array: boolean array with True for pings to keep after subsampling
        :returns boolean for sucess of filter
        '''
    
        # Check number of filtering params
        if len(vals) != 4:
            logging.warning('Incorrect number input values for ringdown filtering')
            return False, False
            
        # Find Sv
        Sv=data.get_Sv()
        # Find vertical range index from the last two entries of filter_values
        range_idx=np.logical_and(Sv.range>=vals[2], Sv.range<=vals[3])
        
        # Find mean Sv in the range across all pings
        # Should probably make this into a method, but good here for now.
        mean_Sv=10*np.log10(np.mean(10**(Sv[:,range_idx]/10), axis=1))
        N = vals[0]
        medians = self.get_running_median(mean_Sv, N)
        
        # Now find pings inside the deviations- the 'good' ones
        return np.logical_and(mean_Sv<medians+vals[1], mean_Sv>(medians-vals[1])),  True
        
        
    def get_running_median(self, m, N):
        '''
        Method to compute running median of m array over N number of samples
        
        :param m: array of samples for median to be computed over
        :type chunk_size: array(int)
        
        :param N: number of samples to find median over
        :type : int
        
        :returns medians array(int) with same length as m
        
        '''
        mid=int((N+1)/2-1)
        count=0
        medians=[]
        running_vals=[]
        for d in m:
            running_vals=np.append(running_vals, d)
            if count>=N:
                #compute median
                temp=np.sort(running_vals)
                medians.append(temp[mid])
            if count>N:
                running_vals=np.delete(running_vals, 0)
            count+=1
        # Add the ends at N/2 to the front and end of the array
        medians=np.insert(medians,0, np.ones(mid)*medians[0])
        medians=np.append(medians, np.ones(mid+1)*medians[-1])
        
        return medians
        
    def remove_intervals(self, idx_ss_array=None):
        '''
        Method to remove intervals and compute stats on filters
        
        :param idx_ss_array: boolean array of pings after subsampling, to start filtering on,
                                    needed to keep track of removed pings within subsample
        :type idx_ss_array: bool array
        
        :returns idx_array: boolean array of pings (by interval) to remove (False) overlaid on subsampling input array
        :returns ping_stats: dictionary with data about ping statistcs
        :returns tracker: dictionary with data on which files and intervals are removed and why
        '''
        if not self.pr_params:
            logging.warning('No ping statistic parameters have been provided, so cannot remove intervals or compute stats')
            return False, False
            
        if not self.filtered_arrays:
            logging.warning('No filtering has been applied, so cannot  remove intervals or compute statistics')
            return False, False
        else:
            ping_stats = {}
            tracker = {}
            interval_tracker = {'removed': [], 'reason': [], 'bounds': None}
            file_tracker = {'removed': [], 'reason': []}
            
            for filt in self.filter_params:
                if idx_ss_array is None:
                        logging.warning('Computing ping statistics on complete pingset, no subsample array was provided')
                        idx_ss_array = np.ones(self.filtered_arrays[filt], dtype=bool)
                is_interval_filter = filt == 'bottom' or filt == 'ringdown'
                if is_interval_filter:
                    ping_stats[filt] = self.get_ping_stats(self.filtered_arrays[filt], idx_ss_array=idx_ss_array)
                    interval_tracker['removed'].append(ping_stats[filt][5])
                    interval_tracker['reason'].append(filt)
                    if interval_tracker['bounds'] is None:
                        interval_tracker['bounds'] = [[a,b] for a,b in zip(ping_stats[filt][0], ping_stats[filt][1])]
                else:
                    ping_stats[filt] = self.get_ping_stats(self.filtered_arrays[filt])
                    if ping_stats[filt][5] == 'Y':
                        if 'Y' in file_tracker['removed']:
                            file_tracker['reason'] = 'Combination'
                        else:
                            file_tracker['removed'] = 'Y'
                            file_tracker['reason'] = filt
                            
            tracker['file_removed'] = file_tracker['removed']
            tracker['file_reason'] = file_tracker['reason']
            tracker['interval_removed'] = []
            tracker['interval_reason'] = []
            if is_interval_filter:
                count = 0 
                for set in np.transpose(interval_tracker['removed']):
                    if 'Y' in set:
                        idx_ss_array[range(interval_tracker['bounds'][count][0], interval_tracker['bounds'][count][1]+1)] = False
                        test = set == 'Y'
                        ind = np.where(test)[0]
                        tracker['interval_removed'].append('Y')
                        if len(ind) > 1:
                            tracker['interval_reason'].append('Both')
                        else:
                            tracker['interval_reason'].append(interval_tracker['reason'][ind[0]])
                    else:
                        tracker['interval_removed'].append('N')
                        tracker['interval_reason'].append('')
                    count += 1
        
        
        return idx_ss_array, ping_stats, tracker
        
    def get_ping_stats(self, idx_array, idx_ss_array=None):
        '''
        Method to compute statistics over specified intervals on percentage of dropped pings
        
        :param idx_array: boolean array of filtered kept (True) and removed (False) pings
        :type idx_array: array(bool)
        
        :optional param idx_ss_array: boolean array of subsampled filtered data to compare
        :type idx_ss_array: array(bool)
        
        :returns ping stats: array or set of arrays, defining:
                                    - starting ping for computing stat on a set
                                    - number of pings removed for a set
                                    - total pings for a set
                                    - percent removed in a set
        :type ping stats: array(int) or set of array(int)
        
        '''
        if idx_array is None:
            return [np.nan, np.nan, np.nan, np.nan, np.nan, 'N']
        # Find percent of dropped pings by 'set' specified in self.pr_params
        if idx_ss_array is None:
            # This is an easy case- a reference boolean array was not passed in,
            # so compute statistics over the entire file
            number_of_pings_removed = len(np.where(np.logical_not(idx_array))[0])
            total_number_of_pings = len(idx_array)
            percent = number_of_pings_removed * 100 / total_number_of_pings
            start_pings = 0
            end_pings = len(idx_array)-1
            if percent == 100:
                removed_interval = 'Y'
            else:
                removed_interval = 'N'
            
        else:
            # Here evaluate the number of pings in the subsampled array that have been dropped in intervals specified
            ind = np.where(idx_ss_array)
            count = 1
            pings_removed = 0
            start_pings = []
            end_pings = []
            number_of_pings_removed = []
            total_number_of_pings =[]
            percent = []
            removed_interval = []
            for index in ind[0]:
                if count == 1:
                    start_pings.append(index)
                
                if not idx_array[index]:
                    pings_removed += 1
                
                if count == self.pr_params['statistic_interval']:
                    number_of_pings_removed.append(pings_removed)
                    total_number_of_pings.append(count)
                    percent.append(pings_removed * 100 / count)
                    end_pings.append(index)
                    if pings_removed * 100 / count >= self.pr_params['threshold_to_remove']:
                        removed_interval.append('Y')
                    else:
                        removed_interval.append('N')
                    count = 1
                    pings_removed = 0
                else:
                    count += 1
            
        ping_stats = [start_pings, end_pings, number_of_pings_removed, total_number_of_pings, percent, removed_interval]
        return ping_stats
