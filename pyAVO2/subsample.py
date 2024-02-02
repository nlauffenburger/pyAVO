# -*- coding: utf-8 -*-

import numpy as np
import logging

class Subsample():
    '''
    Class for subsampling a set of ping data
    '''
    def __init__(self, chunk_size, percent):
        '''
        Initialize subsample class with parameters
        
        :param chunk_size: number of pings in a row to keep for each subsample
        :type chunk_size: int
        
        :param percent: percent of data to subsample
        :type : int
        '''
        
        self.chunk_size = chunk_size
        # Define subsample skip interval- from the beginning of each chunk
        self.skip_number = 100*chunk_size/percent
        
    def subsample(self, total_pings, start_ping):
        '''
        Method to subsample array:
        Use chunk size and skip numbers initialized in class to return
        a boolean array with specified length, subsampled starting
        at input start position (ping)
        
        :param total_pings: total number of pings for a data array to subsample
        :type total_pings: int
        
        :param start_ping: starting ping (index) to start subsample count
        :type start_ping: int
        
        :returns idx_array: boolean array with True for pings to keep after subsampling
        '''
        # Sanity check:
        if start_ping>total_pings:
            logging.error('Start ping is larger than total_pings, subsampling not completed')
            return False, False
        
        idx_array = np.full(total_pings, 0, np.bool_)
        
        # Get array of the start and end point for each chunk
        temp=np.arange(0, total_pings)
        starts=temp[start_ping::int(self.skip_number)]
        stops=starts+self.chunk_size
        
        # Sometimes the final end will be greater than the length of idx_array,
        # so move it back to length of idx_array.
        if stops[-1]>total_pings:
            stops[-1] = total_pings
        
        for j in range(len(starts)):
            idx_array[starts[j]:stops[j]] = True
        
        return idx_array, starts, stops-1, True
