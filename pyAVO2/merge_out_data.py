# -*- coding: utf-8 -*-

import logging
from echolab2.instruments.util.simrad_raw_file import RawSimradFile, SimradEOF
from echolab2.instruments.util import simrad_parsers
from pyAVO2 import avo_db
import datetime

class Merge():
    '''
    Class for combining a multiple out files into a single out file
    '''
    def __init__(self,  load_params):
        '''
        Initialize Merge class with loading parameters
        
        :param load_params
        :type : dict with database connection params
        '''
        
        if not load_params:
            self.need_to_load = False
        else:
            self.need_to_load = True
            self.load_params = load_params
            self.db_manager = avo_db.Connection(user=load_params['user'], 
                password=load_params['password'], dsn=load_params['dsn'],
                                      schema=load_params['schema'])
            self.db_cursor = self.db_manager.cursor()
    
    def merge(self, in_files, out_file_name):
        '''
        Method to read in a list of input out files and combine them into a single file with out_file_name
        '''
        
        bytes_written = 0

        out_fid = open(out_file_name, 'wb')
        
        count=0
        for in_file in in_files:
            in_fid = RawSimradFile(in_file, 'r')
            
            #  read the config datagram
            dgram = in_fid.read(1)

            #  Since this is a config datagram, we use the SimradConfigParser's to_string() method
            #  to generate a stream of bytes to write. FYI, the config datagram type in EK/ES60
            #  files is CON0.
            if count==0:
                bytes_written += out_fid.write(simrad_parsers.SimradConfigParser().to_string(dgram))
                start_time = dgram['timestamp']
                count += 1

            #  read until there is no more data
            more_data = True
            while more_data:

                try:
                    dgram = in_fid.read(1)
                except SimradEOF:
                    #  we're at the end of the file - no more data
                    more_data = False
                    continue

                #  since the different datagrams use different parsers, you have to branch
                #  based on the datagram type. DEP0 is the datagram that has the bottom depths
                #  in an .out file.
                if dgram['type'] == 'DEP0':
                    bytes_written += out_fid.write(simrad_parsers.SimradDepthParser().to_string(dgram))
                    cur_time = dgram['timestamp']
                    count += 1

                #  NME0 are NMEA datagrams - if you want to omit NMEA datagrams from the combined file
                #  you would just not include this block of code.
                if dgram['type'] == 'NME0':
                    bytes_written += out_fid.write(simrad_parsers.SimradNMEAParser().to_string(dgram))

            in_fid.close()
        out_fid.close()
        logging.info("Done. " + str(bytes_written) + " bytes written to file.")
        
        if self.need_to_load:
            base_name = out_file_name[out_file_name.rfind('\\')+1:]
            line = int(base_name[1:5])
            val = self.db_cursor.get_datafile(self.load_params['ship_id'], self.load_params['survey_id'], base_name)
            if not val:
                # If it isn't in the database already, insert it
                self.db_cursor.insert_datafile(self.load_params['ship_id'], self.load_params['survey_id'], return_id=False,
                    line=line, file_name=base_name, start_time=start_time, end_time=cur_time,
                    n_pings=int(count),
                    clock_adj=0,
                    mean_skew=0,
                    stddev_skew=0,
                    status=avo_db.StatusCodes.UNCHECKED)
                logging.info("File name " + str(base_name) + " written to database.")
            self.db_manager.commit()
        
        return True
