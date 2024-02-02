import cx_Oracle as db
import tempfile
import os
import zipfile
import logging
from pyAVO2 import gps_encoding

log = logging.getLogger(__name__)
DEFAULT_DSN = 'AKC1'
DEFAULT_SCHEMA= 'AVOBASE2'

__all__ = ['Connection']

class StatusCodes(object):
    OK          = 0  #No errors encountered
    UNCHECKED   = 1  #Results not verified by QA
    EFILEIO     = -1
    EFILETIME   = -2
    EFILEGAP    = -3
    ESAMPINT    = -4
    EMULTISAMP  = -5
    ENOMEM      = -6
    ENPINGS     = -7
    ENSAMPLES   = -8
    ENOBOT      = -9
    ENOISE      = -10
    ENOCELLS    = -11
    ENOGPS      = -12
    ENONMEA     = -13
    CALDATA     = -14
    EINTERF     = -15
    EFALSEBOT   = -16
    EBADBOT     = -17
    EPULSEL     = -18
    EINTBOT     = -20
    EINVALID    = -30
    EUNKNOWN    = -99

    msg = {
        OK:  'No errors',
        UNCHECKED:  'Results not verified by QA',
        EFILEIO:    'Error loading data from raw files',
        EFILETIME:  'Problem checking data timestamps against original filename',
        EFILEGAP:   'Maximum allowable time gap between files exceeded',
        ESAMPINT:   'Sample interval in file differs from survey calibration settings.',
        EMULTISAMP: 'Multiple sample intervals found in file.',
        ENPINGS:    'Not enough pings in file.',
        ENSAMPLES:  'Pings contain too few samples.',
        ENOBOT:     'No bottom data for file.',
        ENOCELLS:   'Interval contains no integrated layers.',
        ENOGPS:     'Not enough GPS data.',
        ENONMEA:    'No NMEA datagrams available.',
        ENOMEM:     'Not enough memory to process',
        ENOISE:     'No significant targets, interval dominated by receiver noise',
        CALDATA:    'Data acquired during calibration',
        EINTERF:    'Interval contains transceiver cross-talk interference',
        EFALSEBOT:  'False bottom echo (double bottom bounce)',
        EBADBOT:    'Bad bottom track, or bottom track below maximum data depth.',
        EPULSEL:    'Pulse length in raw data does not match calibration parameters set in database', 
        EINTBOT:    'Bottom return included in integration',
        EINVALID:   'Acoustic backscatter not valid for AVO index.',
        EUNKNOWN:   'Unknown error'
    }

    names = {
        OK:  'OK',
        UNCHECKED:  'UNCHECKED',
        EFILEIO:    'EFILEIO',
        EFILETIME:  'EFILETIME',
        EFILEGAP:   'EFILEGAP',
        ESAMPINT:   'ESAMPINT',
        EMULTISAMP: 'EMULTISAMP',
        ENPINGS:    'ENPINGS',
        ENSAMPLES:  'ENSAMPLES',
        ENOBOT:     'ENOBOT',
        ENOCELLS:   'ENOCELLS',
        ENOGPS:     'ENOGPS',
        ENONMEA:    'ENONMEA',
        ENOMEM:     'ENOMEM',
        ENOISE:     'ENOISE',
        EPULSEL:    'EPULSEL', 
        CALDATA:    'CALDATA',
        EINTBOT:    'EINTBOT',
        EUNKNOWN:   'EUNKNOWN'
    }

class Connection(db.Connection):

    def __init__(self, schema=None, **kwargs):
        db.Connection.__init__(self, **kwargs)

        #Set the schema
        self.change_schema(schema)

    def cursor(self):
        return Cursor(self)


    def change_schema(self, schema):

        if schema is None:
            return

        schema = schema.upper()
        cur = self.cursor()

        current_schema = cur.execute("SELECT sys_context('userenv', 'current_schema') from DUAL").fetchall()[0][0]

        if current_schema.upper() != schema:
            cur.execute('ALTER session SET CURRENT_SCHEMA=:schema', schema=schema)

            #Make sure:
            changed_schema = cur.execute("SELECT sys_context('userenv', 'current_schema') from DUAL").fetchall()[0][0]

            if changed_schema != schema:
                cur.close()
                raise ValueError('New schema != desired schema:  (%s != %s)' %(changed_schema, schema))

        cur.close()

    @property
    def connected(self):
        try:
            self.ping()

        except db.InterfaceError:
            return False

        return True


class Cursor(db.Cursor):

    def __init__(self, connection):
        db.Cursor.__init__(self, connection)


    #########################
    # Convenience INSERTions
    ##########################################

    def insert_new_survey(self, ship_id, survey_id, **kwargs):


        __REQUIRED_KWARGS = ['description',
                            'raw_file_path',
                            'output_file_path',
                            'triwave_correct',
                            'triwave_maxgap',
                            'ignore_nmea_checksum',
                            'start_date',
                            'end_date',
                            'interval_length',
                            'layer_thickness',
                            'layer_reference',
                            'max_depth',
                            'min_pings_interval',
                            'max_orphan_gap',
                            'exclude_above_depth',
                            'exclude_below_bottom_offset',
                            'min_threshold',
                            'max_threshold',
                            'do_bottom_integration',
                            'grid_source_id',
                            'year_1_index',
                            'year_2_index',
                            'year_3_index',
                            'year_4_index',
                            'utc_offset']

        list_keys = ['year_1_index', 'year_2_index', 'year_3_index', 'year_4_index']

        for key in __REQUIRED_KWARGS:
            if key not in kwargs:
                raise ValueError('Required keyword argument "%s" missing.' %(key))

            if key in list_keys:
                kwargs[key] = ','.join(map(str, kwargs[key]))

        #  RHT 12/29 - Had to remove "ID=:grid_source_id OR" from the GRID_SOURCE query below since the query would
        #  fail converting the string grid source name into a number for the ID query. Not sure why it worked with
        #  only 1 grid but this started failing when the second grid was added.
        SQL_CMD = \
                """INSERT INTO SURVEY
                    (ID, SHIP_ID, DESCRIPTION, RAW_FILE_PATH,
                    OUTPUT_FILE_PATH, TRIWAVE_CORRECT, TRIWAVE_MAXGAP, IGNORE_NMEA_CHECKSUM,
                    START_DATE, END_DATE, INTERVAL_LENGTH, LAYER_REFERENCE, LAYER_THICKNESS, MAX_DEPTH,
                    MIN_PINGS_INTERVAL, MAX_ORPHAN_GAP, EXCLUDE_ABOVE_DEPTH,
                    EXCLUDE_BELOW_BOTTOM_OFFSET, MIN_THRESHOLD, MAX_THRESHOLD,
                    DO_BOTTOM_INTEGRATION,
                    GRID_SOURCE_ID, YEAR_1_INDEX, YEAR_2_INDEX, YEAR_3_INDEX,
                    YEAR_4_INDEX, UTC_OFFSET)
                VALUES (:id, :ship_id, :description, :raw_file_path,
                    :output_file_path, :triwave_correct, :triwave_maxgap, :ignore_nmea_checksum,
                    :start_date, :end_date, :interval_length, :layer_reference, :layer_thickness, :max_depth,
                    :min_pings_interval, :max_orphan_gap, :exclude_above_depth,
                    :exclude_below_bottom_offset, :min_threshold, :max_threshold,
                    :do_bottom_integration,
                    (SELECT ID FROM GRID_SOURCE WHERE NAME=:grid_source_id),
                    :year_1_index, :year_2_index, :year_3_index, :year_4_index,
                    :utc_offset)"""

        self.execute(SQL_CMD, ship_id=ship_id, id=survey_id, **kwargs)

    def insert_calibration_data(self, ship_id, survey_id, return_id=True, **kwargs):

        __REQUIRED_KWARGS = [
            'absorption_coefficient',
            'equivalent_beam_angle',
            'frequency',
            'gain',
            'echosounder',
            'sample_interval',
            'pulse_length',
            'sa_correction',
            'sound_velocity',
            'transmit_power',
            'ang_ofst_alon',
            'ang_sens_alon',
            'ang_ofst_athw' ,
            'ang_sens_athw',
            'transducer_depth',
            'channel',
            'description']

        for key in __REQUIRED_KWARGS:
            if key not in kwargs:
                raise ValueError('Required keyword argument "%s" missing.' %(key))

        SQL_CMD = \
            """INSERT INTO FREQUENCY
                    (SHIP_ID, SURVEY_ID, FREQUENCY, DESCRIPTION, ECHOSOUNDER,
                    CHANNEL, SOUND_VELOCITY, SAMPLE_INTERVAL, ABSORPTION_COEFFICIENT, GAIN,
                    PULSE_LENGTH, EBA, POWER, SA_CORRECTION, ANG_SENS_ALON, ANG_SENS_ATHW,
                    ANG_OFST_ALON, ANG_OFST_ATHW, TRANSDUCER_DEPTH)
            VALUES (:ship_id, :survey_id, :frequency, :description, :echosounder,
                    :channel, :sound_velocity,:sample_interval, :absorption_coefficient, :gain,
                    :pulse_length, :equivalent_beam_angle, :transmit_power, :sa_correction, :ang_sens_alon, :ang_sens_athw,
                    :ang_ofst_alon, :ang_ofst_athw, :transducer_depth)"""


        params = {'ship_id': ship_id, 'survey_id': survey_id}
        params.update(kwargs)

        if return_id:
            SQL_CMD += " RETURNING ID INTO :r_id"
            db_num = self.var(db.NUMBER)
            params['r_id'] = db_num

        self.execute(SQL_CMD, **params)

        if return_id:
            freq_id = db_num.getvalue()
            return int(freq_id)
        else:
            return None

    def insert_layer(self, ship_id, survey_id, offset, thickness, return_id=True):

        params = dict(ship_id=ship_id, survey_id=survey_id,
            offset=offset, thickness=thickness)

        SQL_CMD=\
        """INSERT INTO LAYERS
        (SHIP_ID, SURVEY_ID, OFFSET, THICKNESS)
        VALUES (:ship_id, :survey_id, :offset, :thickness)"""

        if return_id:
            SQL_CMD += " RETURNING ID INTO :r_id"
            db_num = self.var(db.NUMBER)
            params['r_id'] = db_num

        self.execute(SQL_CMD, **params)

        if return_id:
            layer_id = db_num.getvalue()
            return int(layer_id)
        else:
            return None


    def insert_datafile(self, ship_id, survey_id, return_id=True, **kwargs):

        __REQUIRED_KWARGS = [
            'line',
            'file_name',
            'start_time',
            'end_time',
            'mean_skew',
            'clock_adj',
            'n_pings',
            'status']

        __OPTIONAL_KWARGS = [
            'stddev_skew']

        for key in __REQUIRED_KWARGS:
            if key not in kwargs:
                raise ValueError('Required keyword argument "%s" missing.' %(key))

        for key in __OPTIONAL_KWARGS:
            if key not in kwargs:
                kwargs[key] = None

        params = {'ship_id': ship_id, 'survey_id': survey_id}
        params.update(kwargs)

        SQL_CMD=\
            """INSERT INTO DATA_FILES
            (SHIP_ID, SURVEY_ID, LINE, FILE_NAME, START_TIME, END_TIME, CLOCK_ADJ, MEAN_SKEW, STDDEV_SKEW, N_PINGS, STATUS)
            VALUES (:ship_id, :survey_id, :line, :file_name, :start_time, :end_time, :clock_adj, :mean_skew, :stddev_skew, :n_pings, :status)"""

        if return_id:
            SQL_CMD += " RETURNING ID INTO :r_id"
            db_num = self.var(db.NUMBER)
            params['r_id'] = db_num

        self.execute(SQL_CMD, **params)

        if return_id:
            file_id = db_num.getvalue()
            return int(file_id)
        else:
            return None

    def insert_triwave_results(self, file_id, frequency_id, fit_ping_offset, fit_amp, fit_amp_offset, fit_r2):

        SQL_CMD=\
            """INSERT INTO TRIWAVE_CORRECTION
            (FILE_ID, FREQUENCY_ID, FIT_AMP, FIT_PING_OFFSET, FIT_AMP_OFFSET, FIT_R2)
            VALUES (:file_id, :frequency_id, :fit_amp, :fit_ping_offset, :fit_amp_offset, :fit_r2)"""


        self.execute(SQL_CMD, file_id=file_id, frequency_id=frequency_id, fit_ping_offset=fit_ping_offset,
            fit_amp=fit_amp, fit_amp_offset=fit_amp_offset, fit_r2=fit_r2)

        return None

    def insert_mean_xmit_power(self, file_id, frequency_id, mean_xmit_value):

        SQL_CMD=\
            """INSERT INTO MEAN_XMIT_POWER
            (FILE_ID, FREQUENCY_ID, MEAN_XMIT_VALUE)
            VALUES (:file_id, :frequency_id, :mean_xmit_value)"""


        self.execute(SQL_CMD, file_id=file_id, frequency_id=frequency_id, mean_xmit_value=mean_xmit_value)

        return None

    def insert_interval(self, ship_id, survey_id, frequency_id, return_id=True, **kwargs):

        __REQUIRED_KWARGS = {
            'processor': None,
            'grid_id': None,
            'line':int ,
            'start_lat':float,
            'start_lon':float,
            'end_lat':float,
            'end_lon':float,
            'length':float,
            'width':float,
            'mean_ex_below_depth':float,
            'mean_ex_above_depth':float,
            'bottom_mean_sv':float,
            'start_time':None,
            'end_time':None,
            'mean_speed':float,
            'stdev_speed':float,
            'bottom_mean_sv': float,
            'status':int,
            'process_id':int,
            'echogram_file':None,
            'track':None,
            'bottom_depths': None
        }


        params = {'ship_id': int(ship_id), 'survey_id': int(survey_id), 'frequency_id': int(frequency_id)}

        for key, func in __REQUIRED_KWARGS.items():
            if key not in kwargs:
                raise ValueError('Required keyword argument "%s" missing.' %(key))

            value = kwargs[key]

            if func is None or value is None:
                params[key] =  kwargs[key]

            else:
                params[key] = func(value)

        SQL_CMD = """INSERT INTO INTERVAL
            (SHIP_ID, SURVEY_ID, FREQUENCY_ID, PROCESSOR, GRID_ID, LINE, START_LAT, START_LON,
                END_LAT, END_LON, LENGTH, WIDTH, MEAN_EX_BELOW_DEPTH, MEAN_EX_ABOVE_DEPTH, BOTTOM_MEAN_SV,
                START_TIME, END_TIME, MEAN_SPEED, STDEV_SPEED,
                STATUS, ECHOGRAM_FILE, TRACK, PROCESS_ID, BOTTOM_DEPTHS)
            VALUES (:ship_id, :survey_id, :frequency_id, :processor, :grid_id, :line, :start_lat,
                :start_lon, :end_lat, :end_lon, :length, :width, :mean_ex_below_depth, :mean_ex_above_depth,
                :bottom_mean_sv, :start_time, :end_time, :mean_speed, :stdev_speed,
                :status, :echogram_file, :track, :process_id, :bottom_depths)"""


        if return_id:
            SQL_CMD += " RETURNING ID INTO :r_id"
            db_num = self.var(db.NUMBER)
            params['r_id'] = db_num

        self.execute(SQL_CMD, **params)

        if return_id:
            result = int(db_num.getvalue()[0])
            return result
        else:
            return None

    def insert_interval_source(self, ship_id, survey_id,
            interval_id, filename, position, first_ping, num_pings):


        SQL_CMD = """INSERT INTO INTERVAL_SOURCE (INTERVAL_ID, POSITION, FILE_ID,
            FIRST_PING, NUM_PINGS)
            VALUES  (:interval_id, :position,
                (SELECT ID FROM DATA_FILES WHERE SHIP_ID=:ship_id AND SURVEY_ID=:survey_id AND FILE_NAME=:filename),
                :first_ping, :num_pings)"""

        self.execute(SQL_CMD, ship_id=int(ship_id), survey_id=int(survey_id), filename=filename,
            interval_id=interval_id, position=int(position), first_ping=int(first_ping), num_pings=int(num_pings))

        return None

    def insert_integration_cell(self, interval_id, return_id=True, **kwargs):

        __REQUIRED_KWARGS = {
            'frequency_id': int,
            'min_range': float,
            'max_range': float,
            'mean_range': float,
            'min_depth': float,
            'max_depth': float,
            'mean_depth': float,
            'layer_id': int,
            'class_': None,
            'min_sv': float,
            'max_sv': float,
            'mean_sv': float,
            'abc': float,
            'nasc': float,
            'pings_integrated': int,
            'pings_filtered': int,
            'pings_valid': int,
            'total_samples': int,
            'samples_filtered': int,
            'samples_integrated': int}

        params = {'interval_id': int(interval_id)}

        for key, func in __REQUIRED_KWARGS.items():
            if key not in kwargs:
                raise ValueError('Required keyword argument "%s" missing.' %(key))

            value = kwargs[key]

            if func is None or value is None:
                params[key] =  kwargs[key]

            else:
                params[key] = func(value)

        SQL_CMD = """INSERT INTO INTEGRATION_CELL
            (FREQUENCY_ID, INTERVAL_ID, LAYER_ID, MIN_RANGE, MAX_RANGE, MEAN_RANGE, CLASS,
                MIN_SV, MAX_SV, MEAN_SV, ABC, NASC, TOTAL_SAMPLES, SAMPLES_FILTERED,
                SAMPLES_INTEGRATED, PINGS_INTEGRATED, PINGS_FILTERED, PINGS_VALID,
                MIN_DEPTH, MAX_DEPTH, MEAN_DEPTH)
            VALUES (:frequency_id, :interval_id, :layer_id, :min_range, :max_range, :mean_range,
                :class_, :min_sv, :max_sv, :mean_sv, :abc, :nasc, :total_samples,
                :samples_filtered, :samples_integrated, :pings_integrated, :pings_filtered,
                :pings_valid, :min_depth, :max_depth, :mean_depth)"""

        if return_id:
            SQL_CMD += " RETURNING ID INTO :r_id"
            db_num = self.var(db.NUMBER)
            params['r_id'] = db_num

        self.execute(SQL_CMD, **params)

        if return_id:
            result = int(db_num.getvalue()[0])
            return result
        else:
            return None

    def insert_new_filter(self, frequency_id, filter_name,
        parameters, return_id=True):

        SQL_CMD = """INSERT INTO FILTERS
            (FREQUENCY_ID, FILTER_NAME, PARAMETERS)
            VALUES (:frequency_id, :filter_name, :parameters)"""

        params = dict(frequency_id=int(frequency_id), filter_name=filter_name,
            parameters=parameters)

        if return_id:
            SQL_CMD += " RETURNING ID INTO :r_id"
            db_num = self.var(db.NUMBER)
            params['r_id'] = db_num

        self.execute(SQL_CMD, **params)

        if return_id:
            result = int(db_num.getvalue())
            return result
        else:
            return None

    def insert_filter_results(self, cell_id, filter_id, elements_filtered):

        SQL_CMD = """INSERT INTO FILTER_RESULTS (FILTER_ID, CELL_ID, ELEMENTS_FILTERED)
            VALUES (:filter_id, :cell_id, :elements_filtered)"""


        self.execute(SQL_CMD, filter_id=int(filter_id), cell_id=int(cell_id),
            elements_filtered=int(elements_filtered))

        return None

    def insert_process_id(self, survey_id, ship_id, processor, start_date, stop_date=None,
                          return_id=True):

        SQL_CMD = \
        """INSERT INTO PROCESS_ID (SURVEY_ID, SHIP_ID, PROCESSOR, START_DATE, STOP_DATE)
            VALUES (:survey_id, :ship_id, :processor, :start_date, :stop_date)"""

        params = dict(survey_id=survey_id, ship_id=ship_id, processor=processor,
                      start_date=start_date, stop_date=stop_date)

        if return_id:
            SQL_CMD += " RETURNING ID INTO :r_id"
            db_num = self.var(db.NUMBER)
            params['r_id'] = db_num


        self.execute(SQL_CMD, **params)

        if return_id:
            result = int(db_num.getvalue()[0])
            return result
        else:
            return None


    def insert_log(self, process_id, survey_id, ship_id, code, file_id=None, line=None,
                   message=None):

        SQL_CMD = \
        """INSERT INTO LOG (PROCESS_ID, SURVEY_ID, SHIP_ID, FILE_ID, LINE, CODE, MSG)
            VALUES (:process_id, :survey_id, :ship_id, :file_id, :line, :code, :msg)"""

        params = dict(survey_id=survey_id, ship_id=ship_id, process_id=process_id,
                      file_id=file_id, line=line, code=code,msg=message)
        self.execute(SQL_CMD, **params)

    @classmethod
    def _compress_groundfish_sources(cls, sources):

        fid = tempfile.TemporaryFile()
        zipped_sources = zipfile.ZipFile(fid, mode='w', compression=zipfile.ZIP_DEFLATED)

        for path, dirs, files in os.walk(sources):
            for file_ in files:
                file_path = os.path.join(path, file_)
                zipped_sources.write(file_path)

        zipped_sources.close()

        fid.seek(0)
        buf = fid.read(-1)
        fid.close()

        return buf

    def insert_groundfish_source(self, name, orig_id_field, source, description, return_id=True):

        SQL_CMD = """INSERT INTO GRID_SOURCE (NAME, SOURCE, ORIG_ID_FIELD, DESCRIPTION)
            VALUES (:name, :source, :orig_id_field, :description)"""

        compressed_source = self._compress_groundfish_sources(source)

        source_blob = self.var(db.BLOB)
        source_blob.setvalue(0, compressed_source)

        params = dict(name=str(name), source=source_blob, orig_id_field=str(orig_id_field),
            description=str(description))

        if return_id:
            SQL_CMD += " RETURNING ID INTO :r_id"
            db_num = self.var(db.NUMBER)
            params['r_id'] = db_num

        self.execute(SQL_CMD, **params)

        if return_id:
            result = int(db_num.getvalue())
            return result
        else:
            return None

    def insert_groundfish_cell(self, source_id, orig_id, station_id,
        shape):

        SQL_CMD = """INSERT INTO GRID (SOURCE_ID, ORIG_ID, STATION_ID, SHAPE)
            VALUES (:source_id, :orig_id, :station_id, :shape)"""

        #  hack for FT-AVO: grid ids were in sci-notation so straight conversion
        #  to int fails. Here we convert to float so it can be converted to int below.
        #  Also since the station ID is a string, we need to convert that back to a string
        #source_id = float(source_id)
        #orig_id = float(orig_id)
        #station_id = str(int(float(station_id)))

        print(source_id, orig_id, station_id)

        params = dict(source_id=int(source_id), orig_id=int(orig_id),
            station_id=station_id, shape=str(shape))

        self.execute(SQL_CMD, **params)


    def insert_region_polygon(self, name, source, shape, description, return_id=True):

        SQL_CMD = """INSERT INTO REGION_POLYGON (NAME, SOURCE, SHAPE, DESCRIPTION)
            VALUES (:name, :source, :shape, :description)"""


        if source is not None:
            compressed_source = self._compress_groundfish_sources(source)

            source_blob = self.var(db.BLOB)
            source_blob.setvalue(0, compressed_source)
        else:
            source_blob = None

        params = dict(name=str(name), source=source_blob, shape=str(shape),
            description=str(description))

        if return_id:
            SQL_CMD += " RETURNING ID INTO :r_id"
            db_num = self.var(db.NUMBER)
            params['r_id'] = db_num

        self.execute(SQL_CMD, **params)

        if return_id:
            result = int(db_num.getvalue())
            return result
        else:
            return None


    #  7-10-15 RHT: added this delete_line method to support the reloading of data
    def delete_line(self, ship_id, survey_id, line):
        '''
        delete_line deletes all data associated with a line from interval,
        interval_source, integration_cell and filter_results, triwave-correction and
        data_files for the specified ship, survey, and line. This method is called
        when a raw data files are being reloaded.

        NOTE THAT THIS WILL DELETE ALL OF THE EV DATA TOO!
        '''

        #  get the data_files ID for
        SQL_CMD = """SELECT ID FROM DATA_FILES
                     WHERE SHIP_ID=:ship_id
                     AND SURVEY_ID=:survey_id
                     AND LINE=:line"""
        files = self.execute(SQL_CMD, ship_id=ship_id, survey_id=survey_id, line=line).fetchall()
        nFiles = len(files)

        #  loop through all of the files associated with this line
        for file in files:

            #  first determine all of the intervals belonging to this file
            SQL_CMD = """SELECT INTERVAL.ID FROM INTERVAL
                        INNER JOIN INTERVAL_SOURCE ON INTERVAL.ID=INTERVAL_SOURCE.INTERVAL_ID
                        WHERE INTERVAL_SOURCE.FILE_ID=:file_id"""
            intervals = self.execute(SQL_CMD, file_id=file[0]).fetchall()

            #  even though we're not doing it here, for reference this is how you filter by processor:
    #        SQL_CMD = """SELECT INTERVAL.ID FROM INTERVAL
    #                    INNER JOIN INTERVAL_SOURCE ON INTERVAL.ID=INTERVAL_SOURCE.INTERVAL_ID
    #                    WHERE INTERVAL.FREQUENCY_ID=:frequency_id
    #                    AND INTERVAL_SOURCE.FILE_ID=:file_id
    #                    AND INTERVAL.PROCESSOR NOT LIKE '%EV%'"""

            for interval in intervals:
                #  now determine all of the cell ids for this interval
                SQL_CMD = """SELECT id FROM INTEGRATION_CELL WHERE interval_id=:interval_id"""
                cells = self.execute(SQL_CMD, interval_id=interval[0]).fetchall()

                #  delete the cell reference data
                for cell in cells:
                    #  delete the filter results
                    SQL_CMD = """DELETE FROM FILTER_RESULTS WHERE cell_id=:cell_id"""
                    self.execute(SQL_CMD, cell_id=cell[0])
                    #  delete integration results
                    SQL_CMD = """DELETE FROM INTEGRATION_CELL WHERE id=:cell_id"""
                    self.execute(SQL_CMD, cell_id=cell[0])

                #  and now delete the interval referenced data

                #  delete interval_source data
                SQL_CMD = """DELETE FROM INTERVAL_SOURCE WHERE interval_id=:interval_id"""
                self.execute(SQL_CMD, interval_id=interval[0])

                #  delete intervals data
                SQL_CMD = """DELETE FROM INTERVAL WHERE id=:interval_id"""
                self.execute(SQL_CMD, interval_id=interval[0])

            #  and lastly, delete the data_file referenced data

            #  first the tri-wave correction data
            SQL_CMD = """DELETE FROM TRIWAVE_CORRECTION WHERE file_id=:file_id"""
            self.execute(SQL_CMD, file_id=file[0])

            #  then the log data...
            SQL_CMD = """DELETE FROM LOG WHERE file_id=:file_id"""
            self.execute(SQL_CMD, file_id=file[0])

            #  lastly the data_files entry
            SQL_CMD = """DELETE FROM DATA_FILES WHERE id=:file_id"""
            self.execute(SQL_CMD, file_id=file[0])

        return nFiles



    #########################
    # Convenience Queries
    ##########################################

    def get_datafile(self, ship_id, survey_id, datafile):
        '''
        Returns a dictionary of file information
        '''

        columns = ['id', 'line', 'file_name', 'start_time', 'end_time', 'clock_adj',
                   'mean_skew', 'stddev_skew', 'n_pings', 'status']
        SQL_COLUMNS = ', '.join([x.upper() for x in columns])

        if isinstance(datafile, str):
            SQL_CMD=\
            """SELECT {column_str} FROM DATA_FILES
                WHERE SHIP_ID=:ship_id
                    AND SURVEY_ID=:survey_id
                    AND FILE_NAME=:datafile""".format(column_str=SQL_COLUMNS)
        else:
            SQL_CMD=\
            """SELECT {column_str} FROM DATA_FILES
                WHERE SHIP_ID=:ship_id
                    AND SURVEY_ID=:survey_id
                    AND ID=:datafile""".format(columns_str=SQL_COLUMNS)


        rows = self.execute(SQL_CMD, ship_id=ship_id, survey_id=survey_id,
                            datafile=datafile).fetchall()

        if len(rows) == 0:
            return {}

        elif len(rows) > 1:
            log.warnging('Multiple files match provided ship/survey/datafile IDs')
            return dict(zip(columns, rows[0]))

        else:
            return dict(zip(columns, rows[0]))

    def get_groundfish_source(self, ident, output_filename=None):

        if isinstance(ident, (int, float)):
            SQL_CMD = """SELECT NAME, SOURCE FROM GRID_SOURCE WHERE ID=:id"""
            rows = self.execute(SQL_CMD, id=int(ident)).fetchall()

        elif isinstance(ident, str):
            SQL_CMD = """SELECT NAME, SOURCE FROM GRID_SOURCE WHERE NAME=:id"""
            rows = self.execute(SQL_CMD, id=str(ident)).fetchall()
        else:
            raise KeyError('Polygon ID needs to be of type int or str.')


        if len(rows) == 0:
            raise NameError('No source with id %s' %(str(ident)))

        source_name, source_blob = rows[0]

        if output_filename is None:
            output_filename = os.path.join(os.getcwd(), source_name) + '.zip'


        with open(output_filename, mode='w+b') as fid:
            fid.write(source_blob.read())

    def get_groundfish_grid(self, source_id, to_wgs1984=False):

        columns = ['id', 'orig_id', 'station_id', 'shape']

        SQL_COLUMNS = ', '.join([x.upper() for x in columns])

        if isinstance(source_id, (int, float)):
            SQL_CMD = """SELECT ID, ORIG_ID, STATION_ID, SHAPE
                FROM GRID WHERE SOURCE_ID=:source_id"""
            rows = self.execute(SQL_CMD, source_id=int(source_id)).fetchall()

        elif isinstance(source_id, str):
            SQL_CMD = """SELECT GRID.ID, ORIG_ID, STATION_ID, SHAPE
                FROM GRID, GRID_SOURCE WHERE NAME=:source_id"""
            rows = self.execute(SQL_CMD, source_id=str(source_id)).fetchall()


        if len(rows) == 0:
            return {}
        else:

            result_dict = {}

            for row in rows:
                grid_id, orig_id, station_id, enc_shape = row
                cell_boundary = gps_encoding.decode_line(enc_shape)

                result_dict[grid_id] = {
                    'orig_id':orig_id,
                    'station_id':station_id,
                    'polygon':cell_boundary
                }

            if to_wgs1984:
                for cell in result_dict.itervalues():
                    cell['polygon'] = gps_encoding.convert_avo_to_wgs1948(cell['polygon'], lon_col=1, inplace=False)

            return result_dict


    def get_region_polygon_source(self, id, output_filename=None):

        SQL_CMD = """SELECT NAME, SOURCE FROM REGION_POLYGON WHERE ID=:id"""


        rows = self.execute(SQL_CMD, id=int(id)).fetchall()

        if len(rows) == 0:
            raise NameError('No source with id %d' %(int(id)))

        source_name, source_blob = rows[0]

        if source_blob is None:
            raise ValueError('Region source shapefile not loaded into database')

        if output_filename is None:
            output_filename = os.path.join(os.getcwd(), source_name) + '.zip'


        with open(output_filename, mode='w+b') as fid:
            fid.write(source_blob.read())

    def get_region_polygon_shape(self, ident):

        if isinstance(ident, (int, float)):
            SQL_CMD = """SELECT NAME, SHAPE FROM REGION_POLYGON WHERE ID=:id"""
            rows = self.execute(SQL_CMD, id=int(ident)).fetchall()
        elif isinstance(ident, str):
            SQL_CMD = """SELECT NAME, SHAPE FROM REGION_POLYGON WHERE NAME=:id"""
            rows = self.execute(SQL_CMD, id=str(ident)).fetchall()
        else:
            raise KeyError('Polygon ID needs to be of type int or str.')

        if len(rows) == 0:
            raise NameError('No source with id %s' %(str(ident)))

        source_name, shape = rows[0]

        return gps_encoding.convert_avo_to_wgs1948(gps_encoding.decode_line(shape), lon_col=1, inplace=False)

    def get_calibration(self, ship_id, survey_id, get_filters=True, frequency=None, channel=None):

        columns = ['id', 'ship_id', 'survey_id', 'frequency', 'description', 'echosounder', 'channel',
            'sound_velocity', 'sample_interval', 'absorption_coefficient', 'gain', 'pulse_length', 'eba',
            'power', 'sa_correction', 'ang_sens_alon', 'ang_sens_athw', 'ang_ofst_alon', 'ang_ofst_athw',
            'transducer_depth']

        key_translations = {'eba': 'equivalent_beam_angle', 'power': 'transmit_power',
                            'ang_ofst_alon': 'angle_offset_alongship',
                            'ang_ofst_athw': 'angle_offset_athwartship',
                            'ang_sens_alon': 'angle_sensitivity_alongship',
                            'ang_sens_athw': 'angle_sensitivity_athwartship'}

        SQL_COLUMNS = ', '.join([x.upper() for x in columns])
        SQL_CMD = "SELECT {column_str} FROM FREQUENCY WHERE SHIP_ID=:ship_id AND SURVEY_ID=:survey_id".format(column_str=SQL_COLUMNS)


        rows = self.execute(SQL_CMD, ship_id=ship_id, survey_id=survey_id).fetchall()
        results = []

        for row in rows:
            result_dict = {}
            for indx, key in enumerate(columns):

                if key in key_translations:
                    key = key_translations[key]

                result_dict[key] = row[indx]

            if (frequency is not None) and (result_dict['frequency'] != frequency):
                continue

            if (channel is not None) and (result_dict['channel'] != channel):
                continue

            results.append(result_dict)

        if get_filters:
            filters = self.get_filters(ship_id=ship_id, survey_id=survey_id)
            for cal_dict in results:
                freq_id = cal_dict['id']
                cal_dict.update(filters=filters.get(freq_id, {}))

        return results



    def get_survey(self, ship_id, survey_id):

        columns = ['id', 'ship_id', 'description',
            'raw_file_path', 'output_file_path', 'triwave_correct', 'triwave_maxgap',
            'ignore_nmea_checksum', 'start_date', 'end_date', 'interval_length',
            'layer_thickness', 'layer_reference', 'max_depth', 'min_pings_interval', 'max_orphan_gap',
            'exclude_above_depth', 'exclude_below_bottom_offset', 'min_threshold',
            'max_threshold', 'do_bottom_integration',
            'grid_source_id', 'year_1_index', 'year_2_index', 'year_3_index', 'year_4_index',
            'utc_offset', 'layer_reference']

        key_translations = {}
        bool_keys = ['triwave_correct', 'ignore_nmea_checksum','do_bottom_integration']
        list_keys = ['year_1_index', 'year_2_index', 'year_3_index', 'year_4_index']
        SQL_COLUMNS = ', '.join([x.upper() for x in columns])
        SQL_CMD = "SELECT {column_str} FROM SURVEY WHERE SHIP_ID=:ship_id AND ID=:survey_id".format(column_str=SQL_COLUMNS)

        rows = self.execute(SQL_CMD, ship_id=ship_id, survey_id=survey_id).fetchall()

        if len(rows) == 0:
            return {}

        else:

            result_dict = {}
            for indx, key in enumerate(columns):

                value = rows[0][indx]

                if key in list_keys:
                    if value:
                        value = value.split(',')
                    else:
                        value = []

                if key in bool_keys:
                    if int(value):
                        value = True
                    else:
                        value = False

                if key in key_translations:
                    key = key_translations[key]

                result_dict[key] = value

            return result_dict


    def get_filters(self, ship_id, survey_id, frequency_ids=None, names=None):

        columns = ['id', 'frequency_id', 'filter_name', 'parameters']

        SQL_CMD = """SELECT FILTERS.ID, FREQUENCY_ID, FILTER_NAME, PARAMETERS
            FROM SURVEY, FILTERS WHERE SHIP_ID=:ship_id AND SURVEY.ID=:survey_id"""

        rows = self.execute(SQL_CMD, ship_id=ship_id, survey_id=survey_id).fetchall()

        result_dict = {}
        for row in rows:

            filter_id, freq_id, filter_name, parameters = row

            if frequency_ids is not None:
                if freq_id not in frequency_ids:
                    continue

            if names is not None:
                if filter_name not in names:
                    continue


            param_dict = eval(parameters)

            this_filter = {'id': filter_id,
                           'params': param_dict
                           }

            try:
                result_dict[freq_id].update({filter_name: this_filter})
            except KeyError:
                result_dict[freq_id] = {filter_name: this_filter}

        return result_dict
