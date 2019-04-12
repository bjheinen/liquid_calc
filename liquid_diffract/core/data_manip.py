# -*- coding: utf-8 -*-
"""
Accessory functions for data manipulation
"""
__author__ = "Benedict J Heinen"
__copyright__ = "Copyright 2018, Benedict J Heinen"
__email__ = "benedict.heinen@gmail.com"

import numpy as np
import scipy.interpolate
from scipy.signal import savgol_filter


def rebin_data(x, y, dq=0.02):
    '''
    Rebins data via interpolation to a set step size.
    Also extrapolates to zero
    '''
    x_rebin = np.arange(0, x[-1], dq)
    f_interp = scipy.interpolate.interp1d(x, y, kind='cubic', fill_value='extrapolate')
    y_rebin = f_interp(x_rebin)
    return x_rebin, y_rebin
    
def convert_two_theta(two_theta, wavelength):
    '''
    Convert 2theta data to Q space
    '''
    q_data = (4 * np.pi / wavelength) * np.sin(np.radians(two_theta)/2)
    return q_data

def zero_norm(int_func, _S_inf):
    '''
    Shift data to fit first value to zero - S_inf
    '''
    shift = int_func[0] 
    int_func = int_func - shift
    return int_func

def bkg_scaling_residual(bkg_scaling, *args):
    (data, bkg) = args
    return np.mean(np.abs(data - (bkg*bkg_scaling)))


def smooth_data(data, method='savitzky-golay', window_length=31, poly_order=3):
    '''
    Returns smoothed y data by applying a savitsky-golay filter
    '''
    if method == 'savitzky-golay':
        return savgol_filter(data, window_length, poly_order)