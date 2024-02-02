# -*- coding: utf-8 -*-
import csv, os, logging, re, datetime, time
import numpy as np
from pyAVO2 import gps_encoding
from shapely.geometry import Polygon, LineString, Point
from pyAVO2.gps_encoding import convert_wgs1984_to_avo
from pyAVO2.avo_db import StatusCodes

PROCESSOR_NAME = 'pyAVO EV'
NULL = None

log = logging.getLogger(__name__)


CSV_NAME_PARSER_2006 = re.compile(r'(?P<boat>[A-Za-z]+)_L(?P<line>[0-9]+)_yr1-Svfilt-ABIN.csv')
CSV_NAME_PARSER_2007 = re.compile(r'(?P<boat>[A-Za-z]+)(?P<year>[0-9]+)_(?P<line>[0-9]+)-Svfilt-ABIN.csv')

CSV_NAME_FMT_ENUM = [
                    #0 - 2006 naming convention  e.g. Arcturus_L0102_yr1-Svfilt-ABIN.csv
                    CSV_NAME_PARSER_2006,
                    #1 - 2007 naming convertion  e.g. Arc2007_002-Svfilt-ABIN.csv
                    CSV_NAME_PARSER_2007
                    ]

def parse_csv_date(csv_date):
    '''
    :param csv_date:  Date from CSV file in YYYYMMDD format.
    :type csv_date: str

    :returns: :class:datetime.date
    '''
    return datetime.datetime.strptime(csv_date, '%Y%m%d').date()

def parse_csv_time(csv_time):
    '''
    :param csv_time:  Time from CSV file in HH:MM:SS.ssss format.
    :type csv_time: str

    :returns: :class:datetime.time
    '''
    return datetime.datetime.strptime(csv_time, '%H:%M:%S.%f').time()

CSV_DATA_FMT = \
    [('REGION_ID', int),
     ('REGION_NAME', str),
     ('REGION_CLASS', str),
     ('PROCESS_ID', int),
     ('INTERVAL', int),
     ('LAYER', int),
     ('SV_MEAN', float),
     ('SV_MAX', float),
     ('SV_MIN', float),
     ('SAMPLES', int),
     ('PRC_NASC', float),
     ('LAYER_DEPTH_MIN', float),
     ('LAYER_DEPTH_MAX', float),
     ('START_PING', int),
     ('END_PING', int),
     ('START_DIST', float),
     ('END_DIST', float),
     ('START_DATE', parse_csv_date),
     ('START_TIME', parse_csv_time),
     ('END_DATE', parse_csv_date),
     ('END_TIME', parse_csv_time),
     ('START_LAT', float),
     ('START_LON', float),
     ('END_LAT', float),
     ('END_LON', float),
     ('EXCLUDE_BELOW_MEAN_DEPTH', float),
     ('PROGRAM_VERSION', str),
     ('PROCESSING_DATE', parse_csv_date),
     ('PROCESSING_TIME', parse_csv_time),
     ('EV_FILENAME', str),
     ('MINIMUM_SV_THRESHOLD_APPLIED', int),
     ('MINIMUM_INTEGRATION_THRESHOLD', float),
     ('MAXIMUM_SV_THRESHOLD_APPLIED', int),
     ('MAXIMUM_INTEGRATION_THRESHOLD', float),
     ('EXCLUDE_ABOVE_LINE_APPLIED', int),
     ('EXCLUDE_ABOVE_MEAN_DEPTH', float),
     ('EXCLUDE_BELOW_LINE_APPLIED',int),
     ('BAD_DATA_SAMPLES', int),
     ('NO_DATA_SAMPLES', int),
     ('NUM_SAMPLES', int),
     ('NUM_BAD_DATA_SAMPLES', int),
     ('NUM_NO_DATA_SAMPLES', int)]

CSV_HEADER, CSV_HEADER_FMT = zip(*CSV_DATA_FMT)

CELL_ITEMS = [\
#     'REGION_ID',
     'REGION_NAME',
     'REGION_CLASS',
#     'PROCESS_ID',
     'INTERVAL',
     'LAYER',
     'SV_MEAN',
     'SV_MAX',
     'SV_MIN',
     'SAMPLES',
     'PRC_NASC',
     'LAYER_DEPTH_MIN',
     'LAYER_DEPTH_MAX',
     'START_PING',
     'END_PING',
     'START_DIST',
     'END_DIST',
     'START_DATE',
     'START_TIME',
     'END_DATE',
     'END_TIME',
     'START_LAT',
     'START_LON',
     'END_LAT',
     'END_LON',
     'EXCLUDE_BELOW_MEAN_DEPTH',
#     'PROGRAM_VERSION',
#     'PROCESSING_DATE',
#     'PROCESSING_TIME',
     'EV_FILENAME',
#     'MINIMUM_SV_THRESHOLD_APPLIED',
#     'MINIMUM_INTEGRATION_THRESHOLD',
#     'MAXIMUM_SV_THRESHOLD_APPLIED',
#     'MAXIMUM_INTEGRATION_THRESHOLD',
#     'EXCLUDE_ABOVE_LINE_APPLIED',
    'EXCLUDE_ABOVE_MEAN_DEPTH',
#     'EXCLUDE_BELOW_LINE_APPLIED',
     'BAD_DATA_SAMPLES',
     'NO_DATA_SAMPLES']
#     'NUM_SAMPLES',
#     'NUM_BAD_DATA_SAMPLES',
#     'NUM_NO_DATA_SAMPLES']

# class HEADER_ENUM(object):
#     '''
#     Column numbers for CSV export files
#     '''
#     REGION_ID                         =  1
#     REGION_NAME                       =  2
#     REGION_CLASS                      =  3
#     PROCESS_ID                        =  4
#     INTERVAL                          =  5
#     LAYER                             =  6
#     SV_MEAN                           =  7
#     SV_MAX                            =  8
#     SV_MIN                            =  9
#     SAMPLES                           = 10
#     PRC_NASC                          = 11
#     LAYER_DEPTH_MIN                   = 12
#     LAYER_DEPTH_MAX                   = 13
#     START_PING                        = 14
#     END_PING                          = 15
#     START_DIST                        = 16
#     END_DIST                          = 17
#     START_DATE                        = 18
#     START_TIME                        = 19
#     END_DATE                          = 20
#     END_TIME                          = 21
#     START_LAT                         = 22
#     START_LON                         = 23
#     END_LAT                           = 24
#     END_LON                           = 25
#     EXCLUDE_BELOW_MEAN_DEPTH          = 26
#     PROGRAM_VERSION                   = 27
#     PROCESSING_DATE                   = 28
#     PROCESSING_TIME                   = 29
#     EV_FILENAME                       = 30
#     MINIMUM_SV_THRESHOLD_APPLIED      = 31
#     MINIMUM_INTEGRATION_THRESHOLD     = 32
#     MAXIMUM_SV_THRESHOLD_APPLIED      = 33
#     MAXIMUM_INTEGRATION_THRESHOLD     = 34
#     EXCLUDE_ABOVE_LINE_APPLIED        = 35
#     EXCLUDE_ABOVE_LINE_DEPTH_MEAN     = 36
#     EXCLUDE_BELOW_LINE_APPLIED        = 37
#     BAD_DATA_SAMPLES                  = 38
#     NO_DATA_SAMPLES                   = 39
#     NUM_SAMPLES                       = 40
#     NUM_BAD_DATA_SAMPLES              = 41
#     NUM_NO_DATA_SAMPLES               = 42


def collect_csv_files(csv_file_path, csv_filename_regex_fmt=0):
    '''
    :param csv_file_path:  Full path to csv file with EV exported data.
    :type csv_file_path: str

    :param csv_filename_regex_fmt:  CSV filename format type.
    :type csv_filename_regex_fmt: int

    :returns: dict

    csv_filename_regex_fmt can take two values:
        0  for the 2006 naming convention  e.g. Arcturus_L0102_yr1-Svfilt-ABIN.csv
        1  for the 2007 naming convertion  e.g. Arc2007_002-Svfilt-ABIN.csv
    
    Returns a dictionary of (line number, filename) pairs
    '''
    csv_file_dict = {}
    pattern_regex = CSV_NAME_FMT_ENUM[csv_filename_regex_fmt]
    line_list = []
    for filename in os.listdir(csv_file_path):
        pattern_match = pattern_regex.match(filename)
        if pattern_match is not None:
            line = int(pattern_match.group('line'))
            if line not in line_list:
                csv_file_dict[line] = [filename]
                line_list.append(line)
            else:
                tmp = csv_file_dict[line]
                tmp.append(filename)
                csv_file_dict[line]=tmp
    
    return csv_file_dict


def read_csv_file(csv_filename):
    '''
    :param csv_filename:  Full path to CSV file
    :type csv_filename: str

    :returns: dict

    Parses EV exported data into a dictionary with the following structure:

    interval_data = {
            interval_number0: [cell_data0, cell_data1,...],
            interval_number1: [cell_data0, cell_data1,...],
            ...
    }

    where interval_number keys are ints and cell_data objects are dictionaries themselves with keys defined by
    csv_loader.CELL_ITEMS
    '''

    interval_data = {}

    with open(csv_filename, 'r') as csv_fid:
        csv_reader = csv.DictReader(csv_fid, fieldnames=CSV_HEADER, dialect='excel', skipinitialspace=True)
        ev_filename = None
        count = 0
        for row in csv_reader:
            #skip first row
            if count==0:
                count+=1
                continue
            class_ = row['REGION_CLASS'].lower().strip('" ')
            num_samples = int(row['SAMPLES'])
            min_sv = float(row['SV_MIN'])
            max_sv = float(row['SV_MAX'])
            mean_sv = float(row['SV_MEAN'])
            
            if class_ == "unclassified":
                err_str = '%s contains unclassified regions, skipping file.' % (csv_filename)
                log.warning(err_str)
                raise ValueError(err_str)


            elif class_ == "":
                if num_samples > 0:
                    err_str = '%s contains data not assigned to a region, skipping file.' % (csv_filename)
                    raise ValueError(err_str)
                else:
                    log.debug('Skipping unassigned region with no data.')
                    continue

            elif class_ == "transmit pulse":
                log.debug('Skipping transmit pulse')
                continue

            elif 9999 in map(abs, [min_sv, max_sv, mean_sv]):
                log.warning('Skipping region w/ bad (9999) values for min_sv, max_sv, or mean_sv')
                continue

            interval_num = int(row['INTERVAL'])
            cell_data_list = interval_data.setdefault(interval_num, [])                
            cell_data_list.append({})
            cell_data = cell_data_list[-1]

            for item_num, item in enumerate(CSV_HEADER):
                if item in CELL_ITEMS:
                    cell_data[item] = CSV_HEADER_FMT[item_num](row[item])

            if ev_filename is None:
                ev_filename = cell_data['EV_FILENAME']

            elif ev_filename != cell_data['EV_FILENAME']:
                raise ValueError(u'Inconsistant Echoview Filenames:  {0} does not match {1}'.format(ev_filename, cell_data['EV_FILENAME']))

    return ev_filename, interval_data

def assert_unique_ev_file(avo_cursor, survey_id, ship_id, ev_filename):
    """
    :param avo_cursor:  AVO database cursor
    :type avo_cursor: :class:`pyavo.avo_db.Cursor`

    :param survey_id:  Survey ID
    :type survey_id: int

    :param ship_id:  Ship ID
    :type ship_id: int

    :param ev_filename:  Echoview filename
    :type ev_filename: str

    :raises ValueError: if a match is found

    Checks the database for previously loaded hand-processed data from a 
    filename matching the one provided by :param ev_filename: for the provided
    :param survey_id:, :param ship_id: pair.  Matches are performed using 
    Oracle's LIKE predicate with a leading wildcard '%' inserted.

        eg.  'some_file.ev' attempts to match with LIKE '%some_file.ev'

    Raises a ValueError if the match is successful.
    """

    SQL = """SELECT DISTINCT process_id FROM interval
    WHERE survey_id=:survey_id
        AND ship_id=:ship_id
        AND echogram_file LIKE :ev_filename"""


    process_ids = [x[0] for x in avo_cursor.execute(SQL, survey_id=survey_id, ship_id=ship_id,
        ev_filename=u'%{0}'.format(ev_filename)).fetchall()]


    if len(process_ids) > 0:
        raise ValueError(u'EV file {0} has already been loaded with process_id:  {1}'.format(ev_filename, process_ids))

    return None

def process_ev_exports(survey_id, ship_id, frequency, db_connection,
                                csv_dir, bad_lines=None, good_lines=None, 
                                commit_results=True, csv_filename_regex_fmt=0):
    '''
    :param survey_id:  Survey ID
    :type survey_id: int

    :param ship_id:  Ship ID
    :type ship_id: int

    :param db_connection:  pyAVO Database Connection
    :type db_connection: :py:class:`avo_db.Connection`

    :param csv_dir:  File path containing exported CSV files.
    :type csv_dir:  str

    :param csv_filename_regex: RegEx returning two named fields:  boat and line
    :type csv_filename_regex:  re.SRE_Pattern

    :param bad_lines:  List of line numbers to skip
    :type bad_lines: list

    :param good_lines:  Only process these lines (Default of None processes all)
    :type good_lines: list
    
    Insert the hand-processed data from exported CSV files into database.

    csv_filename_regex_fmt can take two values:
        0  for the 2006 naming convention  e.g. Arcturus_L0102_yr1-Svfilt-ABIN.csv
        1  for the 2007 naming convertion  e.g. Arc2007_002-Svfilt-ABIN.csv

    '''

    #Get a dictionary of all csv files keyed by line number
    log.info('Searching for CSV files matching pattern in %s ...', csv_dir)
    csv_file_dict = collect_csv_files(csv_dir, csv_filename_regex_fmt)

    
    #Trim lines either explicitly marked BAD or NOT explicitly marked good.
    if bad_lines is not None:
        for line in csv_file_dict.keys():
            if line in bad_lines:
                del csv_file_dict[line]

    if good_lines is not None:
        for line in csv_file_dict.keys():
            if line not in good_lines:
                del csv_file_dict[line]


    lines = sorted(csv_file_dict.keys())
    log.info('Found %d lines:\n    %s', len(lines), lines)    

    avo_cursor = db_connection.cursor()

    log.info('Loading survey info for ship_id: %d, survey_id: %d', ship_id, survey_id)
    survey_info = avo_cursor.get_survey(ship_id=ship_id, survey_id=survey_id)
    if len(survey_info) == 0:
        err_str = "No survey matching ship_id: %d, survey_id: %d" % (ship_id, survey_id)
        raise ValueError(err_str)

    log.info('Loading calibration data for %5.3fkHz', frequency/1000.0)
    calibration_info = avo_cursor.get_calibration(ship_id=ship_id, survey_id=survey_id,
        frequency=frequency)

    if len(calibration_info) == 0:
        err_str = 'No frequency matching %f for shipd_id: %d, survey_id: %d' % (frequency, ship_id, survey_id)
        raise ValueError(err_str)
    elif len(calibration_info) > 1:
        err_str = 'Multiple frequencies matching %f for shipd_id: %d, survey_id: %d' % (frequency, ship_id, survey_id)
        raise NotImplementedError(err_str)

    frequency_id = calibration_info[0]['id']
    log.debug('   Frequency ID:  %d', frequency_id)
    
    #Load Ground Fish Grid info from survey
    log.info('Loading Groundfish grid from database...')
    groundfish_grid_id = survey_info['grid_source_id']
    groundfish_grid    = avo_cursor.get_groundfish_grid(groundfish_grid_id)
    
    log.debug('    Converting grid cells to polygon objects...')
    for grid_info in groundfish_grid.values():
        grid_info['polygon'] = Polygon(grid_info['polygon'])
    

    #Load Layer info from survey
    # log.info('Loading integration layers from database...')
    layer_thickness = survey_info['layer_thickness']
    # layer_offsets   = avo_cursor.get_layers(ship_id=ship_id, survey_id=survey_id)


    #Load data files
    DATA_FILE_SQL=\
    """SELECT LINE,ID,FILE_NAME,START_TIME 
        FROM DATA_FILES 
        WHERE SHIP_ID=:ship_id 
            AND SURVEY_ID=:survey_id
            AND FILE_NAME like '%.raw'
        ORDER BY LINE,START_TIME"""

    data_files = {}
    log.info('Loading raw filenames and info from database...')
    for row in avo_cursor.execute(DATA_FILE_SQL, ship_id=ship_id, survey_id=survey_id):
        line_files = data_files.setdefault(row[0], [])
        line_files.append({'id':row[1],
                           'filename':row[2],
                           'start_time':row[3]})

    # EV_FILE_SQL=\
    # """SELECT ECHOGRAM_FILE 
    #     FROM INTERVAL 
    #     WHERE SHIP_ID=:ship_id 
    #         AND SURVEY_ID=:survey_id 
    #         AND PROCESSOR='pyavo EV'
    # """
    
    # loaded_ev_files = [x[0] for x in avo_cursor.execute(EV_FILE_SQL, ship_id=ship_id, survey_id=survey_id)]

    process_id = avo_cursor.insert_process_id(survey_id=survey_info['id'],
                                 ship_id=survey_info['ship_id'],
                                 processor=PROCESSOR_NAME,
                                 start_date=datetime.datetime.utcfromtimestamp(time.time()),
                                 stop_date=None,
                                 return_id=True)

    log.info('Beginning processing loop...')
    # import pdb; pdb.set_trace()
    for line in lines:
        csv_filenames = csv_file_dict[line]
        for csv_filename in csv_filenames:
            csv_filepath = os.path.join(csv_dir, csv_filename)

            try:
                ev_filename, interval_data = read_csv_file(csv_filepath)
            except ValueError as e:
                log.error(str(e))
                continue

            try:
                assert_unique_ev_file(avo_cursor, survey_id=survey_info['id'], ship_id=survey_info['ship_id'],
                        ev_filename=os.path.basename(ev_filename))
            except ValueError as e:
                log.error(str(e))
                continue

            for interval_num in sorted(interval_data.keys()):
                #Interval-level processing
                cell_data = interval_data[interval_num]

                mean_ex_below_depth = 0

                #Need to find the absolute min/max bounds for an
                #interval. 
                for cell_num in range(len(cell_data)):
                    cell_dict = cell_data[cell_num]
                    start_date = cell_dict['START_DATE']
                    start_time = cell_dict['START_TIME']
                    start_datetime = datetime.datetime(year=start_date.year,
                        month=start_date.month, day=start_date.day,
                        hour=start_time.hour, minute=start_time.minute,
                        second=start_time.second, microsecond=start_time.microsecond)

                    end_date = cell_dict['END_DATE']
                    end_time = cell_dict['END_TIME']
                    end_datetime = datetime.datetime(year=end_date.year,
                        month=end_date.month, day=end_date.day,
                        hour=end_time.hour, minute=end_time.minute,
                        second=end_time.second, microsecond=end_time.microsecond)


                    cell_dict['START_DATETIME'] = start_datetime
                    cell_dict['END_DATETIME'] = end_datetime

                    start_ping = cell_dict['START_PING']
                    end_ping = cell_dict['END_PING']

                    #MEAN_EX_BELOW_DEPTH is a weighted mean across all regions
                    #in this interval 
                    mean_ex_below_depth += cell_dict['EXCLUDE_BELOW_MEAN_DEPTH'] / (end_ping - start_ping + 1)

                start_datetime = min([x['START_DATETIME'] for x in cell_data])
                end_datetime = max([x['END_DATETIME'] for x in cell_data])

                start_indx = [x for (x,y) in enumerate(cell_data) if y['START_DATETIME'] == start_datetime][0]
                end_indx = [x for (x,y) in enumerate(cell_data) if y['END_DATETIME'] == end_datetime][0]


                #Form "GPS Track"  from Start & End lat/lon pairs.  If the starting
                #lat/lon pair is missing (==999), just use the ending lat/lon pair
                #for both.
                
                if cell_data[start_indx]['START_LON'] == 999 or cell_data[start_indx]['START_LAT'] == 999:
                    start_lat = cell_data[start_indx]['END_LAT']
                    start_lon = cell_data[start_indx]['END_LON']
                else:
                    start_lat = cell_data[start_indx]['START_LAT']
                    start_lon = cell_data[start_indx]['START_LON']

                if cell_data[end_indx]['END_LON'] == 999 or cell_data[end_indx]['END_LAT'] == 999:
                    end_lat = cell_data[end_indx]['START_LAT']
                    end_lon = cell_data[end_indx]['START_LON']
                else:
                    end_lat = cell_data[end_indx]['END_LAT']
                    end_lon = cell_data[end_indx]['END_LON']

                if 999 in map(abs, [start_lat, start_lon, end_lat, end_lon]):
                    log.warning('"Undefined lat/lon" remainins.. bad interval num: %d', interval_num)
                    # log.warning('   start lat/lon:  (%f, %f)', start_lat, start_lon)
                    # log.warning('   end   lat/lon:  (%f, %f)', end_lat, end_lon)
                    continue
                    # log.warning('Rolling back changes and skipping line %d', line)
                    # if commit_results:
                    #     db_connection.rollback()

                    # break

                #Convert to AVO coordinates
                gps_track = convert_wgs1984_to_avo(np.array([[start_lat, start_lon], [end_lat, end_lon]]),
                    lon_col=1,is_easterly=True)

                #Store the converted coords back into gps variables
                start_lat, end_lat = gps_track[:, 0]
                start_lon, end_lon = gps_track[:, 1]

                #Identify containing groundfish cell ID.
                #If start_coords == end_coords, we only had 
                #one good gps fix.  Use a Point instead of a LineString
                #for intersection tests.
                if (gps_track[0] == gps_track[1]).all():
                    gps_line = Point(gps_track[0])
                else:
                    gps_line = LineString(gps_track)

                # matching_grid_cells = filter(lambda (x,y): gps_line.intersects(y['polygon']), groundfish_grid.items())
                # if len(matching_grid_cells) == 0:
                #     log.warning('No groundfish cell contains %s', gps_track)
                #     grid_cell_id = None
                # else:
                #     grid_cell_id = matching_grid_cells[0][0]

                matching_grid_cells = [(cell_id, gf_cell['station_id']) for cell_id, gf_cell in groundfish_grid.items() if gps_line.intersects(gf_cell['polygon'])]

                if len(matching_grid_cells) == 0:
                    grid_cell_id = None
                    log.warning('No groundfish cell contains %s', gps_track)
                else:
                    grid_cell_id = matching_grid_cells[0][0]
                #encode line
                track = gps_encoding.encode_line(gps_track)
                
                #distance & width
                distance_nmi = cell_data[end_indx]['END_DIST'] - cell_data[start_indx]['START_DIST']
                width = -1

                #Estimate Speed
                # nmi / s * 3600 s / hr = nmi/hr = knts
                try:
                    mean_speed   = distance_nmi / (end_datetime - start_datetime).total_seconds() * 3600.0
                except ZeroDivisionError:
                    mean_speed = 0
                stdev_speed  = -1

                #Mean excluded depth & bottom integration Sv
                mean_ex_below_depth = cell_data[0]['EXCLUDE_BELOW_MEAN_DEPTH']
                mean_ex_above_depth = cell_data[0]['EXCLUDE_ABOVE_MEAN_DEPTH']
                bottom_mean_sv      = -1

                #Identify original raw filename
                #   We just check against the starting ping timestamp.  We can't 
                #   get a detailed source list because we don't know the individual ping
                #   times
                matching_files = list(filter(lambda y: y['start_time'] <= start_datetime, data_files[line]))
                if len(matching_files) == 0:
                    raise ValueError('Could not find original file for raw data in survey')
                else:
                    raw_filename = matching_files[-1]['filename']
                    # file_id = matching_files[-1]['id']

                #Ping counts
                start_ping = cell_data[start_indx]['START_PING']
                end_ping   = cell_data[end_indx]['END_PING']
                
                pings_integrated = end_ping - start_ping
                total_pings      = pings_integrated

                #bottom integration Sv
                bottom_mean_sv      = -1

                #Create new interval
                #Substitute the echoview line file for the echogram filename
                interval_id = avo_cursor.insert_interval(ship_id=ship_id, survey_id=survey_id,
                    frequency_id=frequency_id, return_id=True, processor=PROCESSOR_NAME,
                    grid_id=grid_cell_id, line=line, start_lat=start_lat, start_lon=start_lon,
                    end_lat=end_lat, end_lon=end_lon, length=distance_nmi, width=width,
                    mean_ex_below_depth=mean_ex_below_depth, mean_ex_above_depth=mean_ex_above_depth,
                    bottom_mean_sv=bottom_mean_sv, start_time=start_datetime, end_time=end_datetime,
                    mean_speed=mean_speed, stdev_speed=stdev_speed, status=StatusCodes.UNCHECKED, 
                    echogram_file=ev_filename, track=track, bottom_depths=None, process_id=process_id)
                
                #Create new interval source
                avo_cursor.insert_interval_source(ship_id=ship_id,
                    survey_id=survey_id, interval_id=interval_id, filename=raw_filename,
                    position=-1, first_ping=0, num_pings=total_pings)

                layer_dict_by_class = {}

                for cell in sorted(cell_data, key=lambda x: int(x['LAYER'])):

                    region_class = cell['REGION_CLASS']
                    layer_dict = layer_dict_by_class.setdefault(region_class, {})

                    #Identify layer ID from min & max depth
                    layer_id = int(cell['LAYER_DEPTH_MIN'] / layer_thickness)

                    if layer_id is None:
                        raise ValueError('No matching layer for interval %d, layer %d' % (cell['INTERVAL'], cell['LAYER_DEPTH_MIN']))

                    accum_layer = layer_dict.setdefault(layer_id,
                        dict(frequency_id=frequency_id,
                             min_range=cell['LAYER_DEPTH_MIN'],
                             max_range=cell['LAYER_DEPTH_MAX'],
                             mean_range=1.5*cell['LAYER_DEPTH_MAX'] - 0.5*cell['LAYER_DEPTH_MIN'],
                             min_depth=cell['LAYER_DEPTH_MIN'],
                             max_depth=cell['LAYER_DEPTH_MAX'],
                             mean_depth=1.5*cell['LAYER_DEPTH_MAX'] - 0.5*cell['LAYER_DEPTH_MIN'],
                             layer_id=layer_id,
                             region_name=cell['REGION_NAME'],
                             min_sv=[],
                             max_sv=[],
                             mean_sv=[],
                             abc=-1,
                             nasc=[],
                             samples=[]))

                    accum_layer['nasc'].append(cell['PRC_NASC'])
                    accum_layer['min_sv'].append(cell['SV_MIN'])
                    accum_layer['max_sv'].append(cell['SV_MAX'])
                    accum_layer['mean_sv'].append(cell['SV_MEAN'])
                    accum_layer['samples'].append(cell['SAMPLES'])

                #Now, for each region class, pull the dictionary of layers
                for region_class, layer_dict in layer_dict_by_class.items():
                    
                    #And for each layer, compute the accumulations across regions
                    for layer_id, accum_layer in layer_dict.items():

                        #For minimum Sv, filter out -999 entries.  Set min_sv = -999 if no
                        #valid entries are to be found
                        filtered_min_sv = list(filter(lambda x: x != -999, accum_layer['min_sv']))
                        if len(filtered_min_sv) > 0:
                            min_sv = min(filtered_min_sv)
                        else:
                            min_sv = -999

                        #Max sv doesn't need to throw out -999 entries 
                        max_sv = max(accum_layer['max_sv'])

                        #Combine individual values of mean Sv (originally in log domain):
                        #  log -> lin -> weighted lin (by sample count) -> sum(weighted lin) -> log
                        accumulated_samples = sum(accum_layer['samples'])
                        weights             = np.array(accum_layer['samples']) / accumulated_samples
                        weighted_mean_sv    = 10 ** (np.array(accum_layer['mean_sv']) / 10.0) * weights
                        accumulated_mean_Sv = 10 * np.log10(np.sum(weighted_mean_sv))
                        
                        #Accumulated NASC is simply the sum across regions
                        accumulated_nasc    = sum(accum_layer['nasc'])

                        avo_cursor.insert_integration_cell(interval_id, return_id=True,
                            frequency_id=frequency_id, 
                            min_range=accum_layer['min_range'],
                            max_range=accum_layer['max_range'],
                            mean_range=accum_layer['mean_range'],
                            min_depth=accum_layer['min_depth'],
                            max_depth=accum_layer['max_depth'],
                            mean_depth=accum_layer['mean_depth'],
                            layer_id=layer_id,
                            class_=region_class, 
                            min_sv=min_sv,
                            max_sv=max_sv, 
                            mean_sv=accumulated_mean_Sv,
                            abc=-1, 
                            nasc=accumulated_nasc,
                            total_samples=accumulated_samples,
                            samples_filtered=0,
                            samples_integrated=accumulated_samples,
                            pings_valid=total_pings,
                            pings_integrated=total_pings,
                            pings_filtered=0)

            log.info('Finished loading line '+str(line)+', file '+csv_filename+' ...')

    log.info('    Commiting changes ...')
    db_connection.commit()

