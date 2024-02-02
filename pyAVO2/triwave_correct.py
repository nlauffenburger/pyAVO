
import numpy as np
from scipy import optimize
import logging

class TriwaveCorrect():
    '''
    Class containing methods for correcting triangle wave noise in data
    '''
    
    def __init__(self, start_sample, end_sample):
        '''
        Initialize triwave correction parameters
        
        :param start_sample: first sample (index) to use in computing mean ringdown
        :type start_sample: int
        
        :param end_sample: last sample (index) to use in computing mean ringdown
        :type end_sample: int
        '''
        
        self.start_sample = start_sample
        self.end_sample = end_sample


    def triwave_correct(self, data_in):
        '''
        Perform correction on raw power data array
        - Compute linear mean of power between start and end samples
        - Fill NaNs with closest earlier neighbor ping
        - Remove spikes in the triwave raw data, using a fixed 0.05 threshold deviation value
        - Fit a triangle
        - Generate an offset array that is the inverse of the fit triangle centered around 0
        - Correct raw power data
        
        :param data: raw data object, which must contain raw power
        :type data: raw_data object derived from pyecholab2 raw_read method
        
        :returns data:  raw data object with corrected raw power
        :returns fit_results: dictionary of parameters of the fit of triangle wave to raw data
        :returns val: bool for success of fit
        '''
        
        L = data_in.n_samples
        try:
            n = np.log10(np.mean(10**(data_in.power[:,self.start_sample:self.end_sample]), axis=1))
        except NameError:
            logging.error("No raw power defined in raw data object.")
            return data_in, False, False
            
        # fill nans with closest earlier ping
        nan_inds = np.argwhere(np.isnan(n))
        while np.any(nan_inds):
            n[nan_inds] = n[nan_inds-1]
            nan_inds = np.argwhere(np.isnan(n))
        
        # fill infs
        inf_inds = np.argwhere(np.isinf(n))
        if not len(n)==len(inf_inds):
            while np.any(inf_inds):
                n[inf_inds] = n[inf_inds-1]
                inf_inds = np.argwhere(np.isinf(n))
        
        # stomp down spikes- 0.05 dB is a good threshold for amplitude of 1 dB in power
        #bad_inds = np.argwhere(np.diff(n)<-0.05)+1
        #while np.any(bad_inds):
        #    n[bad_inds] = n[bad_inds-1]
        #    bad_inds = np.argwhere(np.diff(n)<-0.05)+1
        
        # Fit triangle to ringdown array
        fit_results= self.fit_triangle(n)
        if fit_results['r_squared'] < 0.9:
            logging.warning("Bad triangle fit with r^2 of {}".format(fit_results['r_squared']))
        else:
            logging.info("Triangle fit with r^2 of {}".format(fit_results['r_squared']))
        
        # Find correction triangle
        generated_triangle_offset = self.general_triangle(np.arange(data_in.shape[0]), A=fit_results['amplitude'],
                    M=2721.0, k = fit_results['period_offset'], C=0, dtype='float32')
        triangle_matrix_correct = np.array([generated_triangle_offset,]*L).transpose()
        
        # Correct raw power in data object
        data_in.power = data_in.power - triangle_matrix_correct
        logging.info("Successfully corrected triangle wave noise in raw power data")
        
        return data_in, fit_results, True
        
        
    def fit_triangle(self, mean_ringdown_vec, amplitude=None, period_offset=None,
                          amplitude_offset=None):
        '''
        :param mean_ringdown_vec:  Array of ping ringdown values.
        
        :returns: k, C, R^2
        
        Attempts to fit the values in mean_ringdown_vec to the triangle
        wave offset.  This function returns the two values, k and C.  k is
        the sample offset from period origin (where the first ping lies along
        the triangle period), C is the mean offset of the triangle wave.  R
        is the "R^2" value of the fit (Coefficient of determination)
        
        '''
        N = len(mean_ringdown_vec)
        n = np.arange(N)
        
        fit_func = lambda p: self.general_triangle(n, p[0], 2721.0, p[1], p[2])
        err_func = lambda p: (mean_ringdown_vec-fit_func(p))
        
        if period_offset is None:
            period_offset = 1360 - np.argmax(mean_ringdown_vec)
            
        if amplitude is None:
            amplitude = 1.0
            
        if amplitude_offset is None:
            amplitude_offset = np.mean(mean_ringdown_vec)
            
        guess = [amplitude, period_offset, amplitude_offset]
    
        fit_results = optimize.leastsq(err_func, guess[:], full_output=True)
        
        fit_params, fit_cov, fit_info, fit_msg, fit_success = fit_results
        
        SStot = sum((mean_ringdown_vec - mean_ringdown_vec.mean())**2)
        
        SSerr = sum(err_func(fit_params)**2)
    
        fit_r_squared = 1 - SSerr/SStot
        
        fit_amplitude, fit_period_offset, fit_amplitude_offset = fit_params
        
        #Negative amplitude -> half-period offset.
        if fit_amplitude < 0:
            fit_amplitude = -fit_amplitude
            fit_period_offset += 2721.0 / 2
        fit_period_offset = fit_period_offset % 2721
        
        if abs(fit_period_offset - 2721) < abs(fit_period_offset):
            fit_period_offset -= 2721

        return dict(period_offset=fit_period_offset,
                    amplitude_offset=fit_amplitude_offset,
                    amplitude=fit_amplitude,
                    r_squared=fit_r_squared)
    
    
    def general_triangle(self, n, A=0.5, M=2721,  k=0, C=0, dtype=None):
        '''
        Finds a general triangle-wave function centered at 0 
        
        :param n: sample index
        :type n: array(int)
        
        :param A: Triangle wave amplitude (1/2 peak-to-peak)
        :type A: float
        
        :param M: Triangle wave period in samples
        :type M: int
        
        :param k: Sample offset
        :type k: int
        
        :param C: Amplitude offset
        :type C: float
        
        :returns triangle: array(int) with the same length as n
        
        '''
        n_div_M = ((n + k) % M) / float(M)
        triangle =  A*(2*abs(2 * (n_div_M - np.floor(n_div_M + 0.5))) - 1) + C
        
        if dtype is not None:
            return triangle.astype(dtype)
        else:
            return triangle
        
