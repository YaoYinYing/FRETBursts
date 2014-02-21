# -*- coding: utf-8 -*-
"""
This module contains core functions to read and process timestamps
generated by Manta detector or by NI hardware.
"""

import numpy as np
from pytables_array_list import PyTablesList


def load_manta_timestamps(fname, format='xa', full_output=False,
                          i_start=0, i_stop=None, debug=False):
    """Load manta-timestamps data from `fname`.

    Parameters
    ----------
    fname : (string)
        name of the file containing the data
    format : (string)
        Select a data format. Use **raw** for unmodified manta timestamps
        as saved by Luca's VI; **xa** for the format save by Xavier VI.
    debug : (boolean)
        enable additional safety-checks.
    i_start, i_stop : (integers)
        load timestamps between index start and stop (default: load them all)

    Returns
    -------
    timestamps : list of arrays
        each list element is an array of timestamps for one ch.
    big_fifo_full : list of arrays
        each list element is a bool array of big-FIFO-full flags.
    small_fifo_full : list of arrays
        each list element is a bool array of small-FIFO-full flags.
    """
    assert format in ['raw', 'xa']
    if format == 'raw':
        data = load_raw_manta_data(fname)
    elif format == 'xa':
        data = load_xavier_manta_data(fname,
                    i_start=i_start, i_stop=i_stop, debug=debug)
    timestamps, det = get_timestamps_detectors(data, nbits=24)
    timestamps_m, big_ff, small_ff = process_timestamps(
            timestamps, det, fifo_flag=True, debug=debug)
    if full_output:
        return timestamps_m, big_ff, small_ff, timestamps, det
    else:
        return timestamps_m, big_ff, small_ff


def load_ni_timestamps(fname, debug=False):
    """Load from `fname` manta timestamps acquired by NI card.

    Parameters
    ----------
    fname : string
        name of the file containing the data
    debug : boolean
        enable additional safety-checks.

    Returns
    -------
    timestamps : list of arrays
        each list element is an array of timestamps for one ch.
    big_fifo_full : list of arrays
        each list element is a bool array of big-FIFO-full flags.
    small_fifo_full : list of arrays
        each list element is a bool array of small-FIFO-full flags.
    """
    data = load_xavier_manta_data(fname, dtype='>u4')
    timestamps, det = get_timestamps_detectors(data, nbits=24)
    return process_timestamps(timestamps, det, fifo_flag=False, debug=debug)


def load_xavier_manta_data(fname, skip_lines=3, dtype='>u4',
                           i_start=0, i_stop=None, debug=False):
    """Load manta-timestamps data from `fname` saved from Xavier VI.
    Returns the unprocessed uint32 words containing detector and timestamp.
    """
    f = open(fname, 'rb')
    # Discard a some lines used for header
    for x in range(skip_lines):
        f.readline()
    if debug:
        old_pos = f.tell()
    # Load the rest of the file in buff
    dt = np.dtype(dtype)
    f.seek(f.tell() + dt.itemsize*i_start)
    if i_stop is None:
        i_stop = -1
    if debug:
        assert f.tell() == old_pos + dt.itemsize*i_start
    buff = f.read(dt.itemsize*i_stop)
    return np.ndarray(shape=(len(buff)/dt.itemsize,), dtype=dt, buffer=buff)

def load_raw_manta_data(fname, dtype='<u4'):
    """Load manta-timestamps data from `fname` saved from Luca's VI.
    Returns the unprocessed uint32 words containing detetctor and timestamp.
    """
    return np.fromfile(fname, dtype=dtype)

def get_timestamps_detectors(data, nbits=24):
    """From raw uint32 words extrac timestamps and detector information.
    Returns two arrays: timestamps (uint32) and detectors (uint8).
    """
    det = np.right_shift(data, nbits) + 1
    timestamps = np.bitwise_and(data,  2**nbits - 1)
    return timestamps, det

def process_timestamps(timestamps, det, delta_rollover=1, nbits=24,
                       fifo_flag=True, debug=False):
    """Process 32bit timestamps to correct rollover and sort channels.

    Parameters
    ----------
    timestamps : array (uint32)
        timestamps to be processes (rollover correction and ch separation)
    det : array (int)
        detector number for each timestamp
    nbits : integer
        number of bits used for the timestamps. Default 24.
    delta_rollover : positive integer
        Sets the minimum negative difference between two consecutive timestamps
        that will be recognized as a rollover. Default 1.
    debug : boolean
        enable additional consistency checks and increase verbosity.

    Returns
    -------
    3 lists of arrays (one per ch) for timestamps (int64), big-FIFO full-flags
    (bool) and small-FIFO full flags (bool).
    """
    cumsum, diff = np.cumsum, np.diff
    max_ts = 2**nbits

    zero_data = (det == 0)
    det = det[-zero_data]
    timestamps = timestamps[-zero_data]

    if fifo_flag:
        full_big_fifo = np.bitwise_and(1, np.right_shift(det,7)).astype(bool)
        full_small_fifo = np.bitwise_and(1, np.right_shift(det,6)).astype(bool)
        det = np.bitwise_and(det, 0x3F)

    if debug :
        assert (det < 49).all()

    full_big_fifo_m = []
    full_small_fifo_m = []
    timestamps_m = []
    for CH in range(1, 49):
        mask = (det == CH)
        times32 = timestamps[mask].astype('int32')
        if fifo_flag:
            full_big_fifo_m.append(full_big_fifo[mask])
            full_small_fifo_m.append(full_small_fifo[mask])
        del mask

        if times32.size >= 3:
            # We need at least 2 valid timestamps and the first is invalid
            times64 = (diff(times32) < -delta_rollover).astype('int64')
            cumsum(times64, out=times64)
            times64 *= max_ts
            times64 += times32[1:]
            del times32
        else:
            # Return an array of size 0 for current ch
            times64 = np.zeros(0, dtype='int64')
        timestamps_m.append(times64)

    return timestamps_m, full_big_fifo_m, full_small_fifo_m

def process_store(timestamps, det, out_fname, delta_rollover=1, nbits=24,
                  fifo_flag=True, debug=False):
    """Process 32bit timestamps to correct rollover and sort channels.

    Parameters
    ----------
    timestamps : array (uint32)
        timestamps to be processes (rollover correction and ch separation)
    det : array (int)
        detector number for each timestamp
    out_fname : string
        file name where to save the processed timestamps
    nbits : integer
        number of bits used for the timestamps. Default 24.
    delta_rollover : positive integer
        Sets the minimum negative difference between two consecutive timestamps
        that will be recognized as a rollover. Default 1.
    debug : boolean
        enable additional consistency checks and increase verbosity.

    Returns
    -------
    3 lists of arrays (one per ch) for timestamps (int64), big-FIFO full-flags
    (bool) and small-FIFO full flags (bool).
    """
    cumsum, diff = np.cumsum, np.diff
    max_ts = 2**nbits

    zero_data = (det == 0)
    det = det[-zero_data]
    timestamps = timestamps[-zero_data]

    if fifo_flag:
        full_big_fifo = np.bitwise_and(1, np.right_shift(det,7)).astype(bool)
        full_small_fifo = np.bitwise_and(1, np.right_shift(det,6)).astype(bool)
        det = np.bitwise_and(det, 0x3F)

    if debug :
        assert (det < 49).all()

    array_list_descr = 'List of arrays of %s (one per ch).'  
    timestamps_m = PyTablesList(
            out_fname, overwrite=True, group_name='timestamps_list',
            group_descr=(array_list_descr % 'timestamps'))
    full_big_fifo_m = PyTablesList(out_fname,
            parent_node='/timestamps_list',
            group_name='big_fifo_full_list',
            group_descr=(array_list_descr % 'big-FIFO'))
    full_small_fifo_m = PyTablesList(out_fname,
            parent_node='/timestamps_list',
            group_name='small_fifo_full_list',
            group_descr=(array_list_descr % 'small-FIFO'))

    for CH in range(1, 49):
        mask = (det == CH)
        times32 = timestamps[mask].astype('int32')
        if fifo_flag:
            big_fifo_i = full_big_fifo[mask]
            #if not big_fifo_i.any(): big_fifo_i = np.array([])
            full_big_fifo_m.append(big_fifo_i)

            small_fifo_i = full_small_fifo[mask]
            #if not small_fifo_i.any(): small_fifo_i = np.array([])
            full_small_fifo_m.append(small_fifo_i)
        del mask

        if times32.size >= 3:
            # We need at least 2 valid timestamps and the first is invalid
            times64 = (diff(times32) < -delta_rollover).astype('int64')
            cumsum(times64, out=times64)
            times64 *= max_ts
            times64 += times32[1:]
            del times32
        else:
            # Return an array of size 0 for current ch
            times64 = np.zeros(0, dtype='int64')
        timestamps_m.append(times64)
    timestamps_m.data_file.flush()
    return timestamps_m, full_big_fifo_m, full_small_fifo_m
    
def load_manta_timestamps_pytables(fname):
    """Load timestamps from HDF5 file `fname` saved with `process_store()`.
    """
    timestamps_m = PyTablesList(fname, group_name='timestamps_list')

    big_fifo = PyTablesList(timestamps_m.data_file,
                            group_name='big_fifo_full_list',
                            parent_node='/timestamps_list')

    small_fifo = PyTablesList(timestamps_m.data_file,
                            group_name='small_fifo_full_list',
                            parent_node='/timestamps_list')

    return timestamps_m, big_fifo, small_fifo