"""
Utility for reading clustered data from MountainSort. Also extended to perform IO functions for MDA format data
"""

import os
import json
import errno
import numpy as np
import matplotlib.pyplot as plt
from mountainlab_pytools import mdaio
from tkinter import Tk, filedialog

# Local imports
import QtHelperUtils
import readTrodesExtractedDataFile3

# TODO: These constants have been duplicated. Need to put all of these togther.
MDA_FILE_EXTENSION = '.mda'
DEFAULT_SEARCH_PATH='/run/media/ag/'
VIDEO_TRACKING_EXTENSION = '.videoPositionTracking'
NPZ_FILE_FORMAT = "Numpy Archive (*.npz)"
RAW_DATA_EXTENSION = '.raw.npz'
FIELD_DATA_EXTENSION = '.fielddata.npz'
DECODED_DATA_EXTENSION = '.bayesian.npz'
SPIKE_SAMPLING_RATE = 30000.0
LFP_SAMPLING_RATE = 1500.0
DECIMATION_FACTOR = 20
TIMESTAMP_LABEL = 'timestamp'
TIMESTAMP_DTYPE = 'uint32'
X_LOC1_LABEL = 'x1'
X_LOC2_LABEL = 'x2'
Y_LOC1_LABEL = 'y1'
Y_LOC2_LABEL = 'y2'
POSITION_DTYPE = 'uint16'

# Module identifier
MODULE_IDENTIFIER = "[MountainViewIO] "

def savePlaceFieldData(field_data, place_field_filename='fielddata', data_dir=None):
    """
    Take place field data as a numpy array and save it to an MDA file.
    :field_data: Place field data to be saved
    :place_field_filename: Either the name of the file, or the complete path to
        be used (in the latter case, data_dir should be set to None)
    :data_dir: Location where place field should be saved (in this case, place
        field filename is the name of the file used.)
    """
    if data_dir is None:
        output_filename = place_field_filename
    else:
        output_filename = QtHelperUtils.get_save_file_name(data_dir, \
                message='Select file to save Place Field data',\
                file_format=NPZ_FILE_FORMAT)

    try:
        np.savez(output_filename, field_data)
        QtHelperUtils.display_information('Place field data written to ' + output_filename)
    except Exception as err:
        QtHelperUtils.display_warning('Unable to write place field data.')
        print(err)

def loadPlaceFieldData(place_field_file=None, data_dir=None):
    """
    Load place field data from the specified file.
    SEE ALSO:
        savePlaceFieldData
    """
    if place_field_file is None:
        place_field_file = QtHelperUtils.get_open_file_name(data_dir, file_format='Place Fields (*.npz)', \
            message='Select place field file')
    try:
        place_field_data = np.load(place_field_file)
    except (FileNotFoundError, IOError) as err:
        QtHelperUtils.display_warning('Unable to read place field data. ' + err)
        return
    return place_field_data['arr_0']

def saveBayesianDecoding(posterior, map_estimate, peak_posterior, decoding_filename='decoded_data', data_dir=None):
    """
    Take Bayesian decoding as a set of 3 numpy arrays (overall posterior, MAP
    estimate and the peak posterior values) for the corresponding MAP estimates
    and save this is in a file.
    :posterior: Decoded posterior for each time bin, at each position bin
    :map_estimate: Decoding time-points and final decoded locations.
    :peak_posterior: The value of the posterio at the map_estimate values.
    :decoding_filename: Either the name of the file, or the complete path to
        be used (in the latter case, data_dir should be set to None). File name
        should have all the information needed to distinguis this file (clip
        description, decoding window and window slide for example.)
    :data_dir: Location where decoded data should be saved (in this case,
        decoding_filename is the name of the file used.)
    """
    if data_dir is None:
        output_filename = decoding_filename
    else:
        output_filename = QtHelperUtils.get_save_file_name(data_dir, \
                message='Select file to save Decoded data',\
                file_format=NPZ_FILE_FORMAT)

    try:
        np.savez(output_filename, posterior, map_estimate, peak_posterior)
        QtHelperUtils.display_information('Decoded data written to ' + output_filename)
    except Exception as err:
        QtHelperUtils.display_warning('Unable to write decoded data. ' + err)

def loadBayesianDecoding(decoding_filename=None, data_dir=None):
    """
    Take Bayesian decoding as a set of 3 numpy arrays (overall posterior, MAP
    estimate and the peak posterior values) for the corresponding MAP estimates
    and save this is in a file.
    INPUT:
    :decoding_filename: Path of the decoded data file.
    :data_dir: Location where decoded data would be saved (start point for file
        dialog)

    RETURNS
    :posterior: Decoded posterior for each time bin, at each position bin
    :map_estimate: Decoding time-points and final decoded locations.
    :peak_posterior: The value of the posterio at the map_estimate values.
    """
    if (decoding_filename is None) or (not os.path.exists(decoding_filename)):
        decoding_filename = QtHelperUtils.get_open_file_name(data_dir, file_format='Bayesian Decoding (*.npz)', \
            message='Select decoded data file.')

    try:
        bayesian_data = np.load(decoding_filename)
        QtHelperUtils.display_information('Decoded data loaded from ' + decoding_filename)
        assert(len(bayesian_data.files) == 3)
    except Exception as err:
        QtHelperUtils.display_warning('Unable to read decoded data.')
        print(err)
        return

    return bayesian_data['arr_0'], bayesian_data['arr_1'], bayesian_data['arr_2']

def saveRawData(clips, position, spikes, sp_locations, raw_filename='decoded_data', data_dir=None):
    """
    Take processed recording as a set of 4 numpy arrays (clips, position,
    spike times and spike locations) and save this is in a file.
    :clips: Time clips for analysis
    :position: Processed position data
    :valid_spikes: Spike times and cluster indices
    :spike_locations: Spike information for each cluster
    :raw_filename: Either the name of the file, or the complete path to
        be used (in the latter case, data_dir should be set to None). File name
        should have all the information needed to distinguis this file (clip
        description, decoding window and window slide for example.)
    :data_dir: Location where raw data should be saved (in this case,
        decoding_filename is the name of the file used.)
    """
    if data_dir is None:
        output_filename = raw_filename
    else:
        output_filename = QtHelperUtils.get_save_file_name(data_dir, \
                message='Select file to save processed data',\
                file_format=NPZ_FILE_FORMAT)

    try:
        np.savez(output_filename, clips, position, spikes, sp_locations)
        QtHelperUtils.display_information('Raw data written to ' + output_filename)
    except Exception as err:
        QtHelperUtils.display_warning('Unable to write raw data. ' + err)

def loadRawData(data_filename=None, data_dir=None):
    """
    Take Bayesian decoding as a set of 3 numpy arrays (overall posterior, MAP
    estimate and the peak posterior values) for the corresponding MAP estimates
    and save this is in a file.
    INPUT:
    :data_filename: Path of the decoded data file.
    :data_dir: Location where decoded data would be saved (start point for file
        dialog)

    RETURNS
    :clips: Time clips for analysis
    :position: Processed position data
    :valid_spikes: Spike times and cluster indices
    :spike_locations: Spike information for each cluster
    """
    if (data_filename is None) or (not os.path.exists(data_filename)):
        data_filename = QtHelperUtils.get_open_file_name(data_dir, file_format='Raw Data (*.npz)', \
            message='Select raw data file.')

    try:
        raw_data = np.load(data_filename)
        QtHelperUtils.display_information('Raw data loaded from ' + data_filename)
        assert(len(raw_data.files) == 4)
    except Exception as err:
        QtHelperUtils.display_warning('Unable to read raw data.')
        print(err)
        return

    return raw_data['arr_0'], raw_data['arr_1'], raw_data['arr_2'], raw_data['arr_3']

def separateSpikesInEpochs(data_dir=None, firings_file='firings.curated.mda', timestamp_files=None, write_separated_spikes=True):
    """
    Takes curated spikes from MountainSort and combines this information with spike timestamps to create separate curated spikes for each epoch

    :firings_file: Curated firings file
    :timestamp_files: Spike timestamps file list
    :write_separated_spikes: If the separated spikes should be written back to the data directory.
    :returns: List of spikes for each epoch
    """
    
    if data_dir is None:
        # Get the firings file
        data_dir = QtHelperUtils.get_directory(message="Select Curated firings location")

    separated_tetrodes = []
    curated_firings = []
    merged_curated_firings = []
    tetrode_list = os.listdir(data_dir)
    for tt_dir in tetrode_list:
        try:
            if firings_file in os.listdir(data_dir+'/'+tt_dir):
                curated_firings.append([])
                separated_tetrodes.append(tt_dir)
                firings_file_location = '/'.join([data_dir, tt_dir, firings_file])
                merged_curated_firings.append(mdaio.readmda(firings_file_location))
                print(MODULE_IDENTIFIER + 'Read merged firings file for tetrode %s!'%tt_dir)
            else:
                print(MODULE_IDENTIFIER + 'Merged firings %s not  found for tetrode %s!'%(firings_file, tt_dir))
        except (FileNotFoundError, IOError) as err:
            print(MODULE_IDENTIFIER + 'Unable to read merged firings file for tetrode %s!'%tt_dir)
            print(err)

    gui_root = Tk()
    gui_root.withdraw()
    timestamp_headers = []
    if timestamp_files is None:
        # Read all the timestamp files
        timestamp_files = filedialog.askopenfilenames(initialdir=DEFAULT_SEARCH_PATH, \
                title="Select all timestamp files", \
                filetypes=(("Timestamps", ".mda"), ("All Files", "*.*")))
    gui_root.destroy()

    for ts_file in timestamp_files:
        timestamp_headers.append(mdaio.readmda_header(ts_file))

    # Now that we have both the timestamp headers and the timestamp files, we
    # can separate spikes out.  It is important here for the timestamp files to
    # be in the same order as the curated firings as that is the only way for
    # us to tell that the firings are being split up correctly.

    print(MODULE_IDENTIFIER + 'Looking at spike timestamps in order')
    print(timestamp_files)

    # First splice up curated spikes into indiviual epochs
    for tt_idx, tt_firings in enumerate(merged_curated_firings):
        for ep_idx, ts_header in enumerate(timestamp_headers):
            if tt_firings is None:
                curated_firings[tt_idx].append(None)
                continue

            n_data_points = ts_header.dims[0]
            print(MODULE_IDENTIFIER + 'Epoch ' + str(ep_idx) + ': ' + str(n_data_points) + ' samples.')
            last_spike_from_epoch = np.searchsorted(tt_firings[1], n_data_points, side='left')-1

            # If there are no spikes in this epoch, there might still be some in future epochs!
            if last_spike_from_epoch < 0:
                tt_firings[1] = tt_firings[1] - float(n_data_points)
                curated_firings[tt_idx].append(None)
                continue

            last_spike_sample_number = tt_firings[1][last_spike_from_epoch]
            print(MODULE_IDENTIFIER + separated_tetrodes[tt_idx] + ': First spike ' + str(tt_firings[1][0])\
                    + ', Last spike ' + str(last_spike_sample_number))
            epoch_spikes = tt_firings[:, :last_spike_from_epoch]
            curated_firings[tt_idx].append(epoch_spikes)

            if last_spike_from_epoch < (len(tt_firings[1]) - 1):
                # Slice the merged curated firing to only have the remaining spikes
                tt_firings = tt_firings[:,last_spike_from_epoch+1:]
                print(MODULE_IDENTIFIER + 'Trimming curated spikes. Aggregate sample start ' + str(tt_firings[1][0]))
                tt_firings[1] = tt_firings[1] - float(n_data_points)
                print(MODULE_IDENTIFIER + 'Sample number trimmed to ' + str(tt_firings[1][0]))
            else:
                print(MODULE_IDENTIFIER + separated_tetrodes[tt_idx] + ', Reached end of curated firings at Epoch ' + str(ep_idx))
                tt_firings = None

    print(MODULE_IDENTIFIER + 'Spikes separated in epochs. Substituting timestamps!')
    # For each epoch replace the sample numbers with the corresponding
    # timestamps. We are going through multiple revisions for this so that we
    # only have to load one timestamp file at a time
    for ep_idx, ts_file in enumerate(timestamp_files):
        epoch_timestamps = mdaio.readmda(ts_file)
        print(MODULE_IDENTIFIER + 'Epoch ' + str(ep_idx))
        for tt_idx, tt_curated_firings in enumerate(curated_firings):
            if tt_curated_firings[ep_idx] is None:
                continue
            # Need to use the original array because changes to tt_curated_firings do not get copied back
            curated_firings[tt_idx][ep_idx][1] = epoch_timestamps[np.array(tt_curated_firings[ep_idx][1], dtype=int)]
            print(MODULE_IDENTIFIER + separated_tetrodes[tt_idx] + ': Samples (' + \
                    str(tt_curated_firings[ep_idx][1][0]) + ', ' + str(tt_curated_firings[ep_idx][1][-1]), ')')

    if write_separated_spikes:
        try:
            for tt_idx, tet in enumerate(separated_tetrodes):
                for ep_idx in range(len(timestamp_files)):
                    if curated_firings[tt_idx][ep_idx] is not None:
                        ep_firings_file_name = data_dir + '/' + tet + '/firings-' + \
                                str(ep_idx+1) + '.curated.mda'
                        mdaio.writemda64(curated_firings[tt_idx][ep_idx], ep_firings_file_name)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                print(MODULE_IDENTIFIER + 'Unable to write timestamped firings!')
                print(exception)
        
    return curated_firings

def loadSpikeTimestamps(data_file=None):
    """
    Load spike timestamps, extracted from the rec file with exportmda
    returns: Timestamps for spike data
    """
    
    if data_file is None:
        ts_file = QtHelperUtils.get_open_file_name(\
                message="Select Timestamp MDA Files", file_format="LFP Data (.dat)")

    # Now that we have the timestamp file, we have to read it
    try:
        timestamps = mdaio.readmda(ts_file)
    except (FileNotFoundError, IOError) as err:
        print(err)
        print('Unable to read TIMESTAMPS file.')
        timestamps = None
    finally:
        return timestamps

def loadClusteredData(data_location=None, firings_file='firings.curated.mda', 
        helper_file='hand_curated.mv2', time_limits=None):
    """
    Load up clustered data and pool it.

    :data_location: Directory which has clustered data from all the tetrodes.
    :time_limits: (Floating Point) Real time limits within which the data should be extracted.
    :returns: Spike data, separated into containers for individual units.
    """

    if data_location is None:
        # Get the location using a file dialog
        data_location = QtHelperUtils.get_directory("Select data location.")

    clustered_spikes = []
    tt_cl_to_unique_cluster_id = {}
    unique_cluster_id = 0
    tetrode_list = os.listdir(data_location)
    for tt_dir in tetrode_list:
        tt_dir_path = os.path.join(data_location, tt_dir)
        if not os.path.isdir(tt_dir_path):
            continue

        if firings_file in os.listdir(tt_dir_path):
            tt_idx = tt_dir.split('nt')[1]
            firings_file_path = os.path.join(tt_dir_path, firings_file) 
            curation_file_path = os.path.join(tt_dir_path, helper_file)
            try:
                # Read the firings file
                firing_data = mdaio.readmda(firings_file_path)
            except Exception as err:
                print('Tetrode ' + tt_dir + 'Unable to read firings file!')
                print(err)
                continue

            try:
                # Read the curation file for info on spike clusters
                with open(curation_file_path, 'r') as f:
                    curation_file = json.load(f)
                # Get all cluster IDs. This includes noise, mua, everything!
                cluster_ids = [int(cl) for cl in curation_file['cluster_attributes'].keys()]
            except (FileNotFoundError, IOError) as err:
                print('Tetrode ' + tt_dir + 'Unable to read curation file.')
                continue

            # Read off spikes for individual clusters and assign unique cluster IDs to them
            if time_limits is not None:
                firing_times = (firing_data[1] - firing_data[1][0])/SPIKE_SAMPLING_RATE
                time_limit_start_idx = np.searchsorted(firing_times, time_limits[0], side='left')
                time_limit_finish_idx = np.searchsorted(firing_times, time_limits[1], side='right')
                firing_data = firing_data[:,time_limit_start_idx:time_limit_finish_idx]
            firing_clusters = firing_data[2]

            n_clusters = 0
            for unit_id in cluster_ids:
                unit_spikes = firing_data[1][firing_clusters == unit_id]
                if len(unit_spikes > 0):
                    tt_cl_to_unique_cluster_id[(tt_idx, unit_id)] = unique_cluster_id
                    n_clusters += 1
                    unique_cluster_id += 1
                    clustered_spikes.append(unit_spikes)
                else:
                    clustered_spikes.append(None)

            n_spikes = len(firing_data[1])
            print('Tetrode %s loaded %d spikes from %d clusters.' %(tt_dir, n_spikes, n_clusters))
        else:
            print('Tetrode ' + tt_dir + ': Firings file not found!')

    return clustered_spikes

def loadPositionData(data_file=None, reset_time=False, time_limits=None):
    """
    Load position data (timestamped) using data_file

    :data_file: VideoTracking file that contains the position data.
    :time_limits: (Floating Point) Real time limits within which the data should be extracted.
    :returns: Timestamped position data
    """
    position_data_type = [(TIMESTAMP_LABEL, TIMESTAMP_DTYPE), 
            (X_LOC1_LABEL, POSITION_DTYPE), (Y_LOC1_LABEL, POSITION_DTYPE),
            (X_LOC2_LABEL, POSITION_DTYPE), (Y_LOC2_LABEL, POSITION_DTYPE)]

    if data_file is None:
        data_file = QtHelperUtils.get_open_file_name(data_dir=DEFAULT_SEARCH_PATH, message="Select Tracking File", \
            file_format="Camera Tracking (*.videoPositionTracking)")
    try:
        position_data_file = open(data_file, 'rb')
    except (FileNotFoundError, IOError) as err:
        print(err)
        return

    for _ in range(8):
        # TODO: Could use the file header to process the information. Right now we will just believe that 
        settings_line = position_data_file.readline()
        if __debug__:
            print(settings_line)

    try:
        position_data = np.fromfile(position_data_file, dtype=position_data_type)
    except Exception as err:
        print(err)
        return

    first_position_timestamp = position_data[TIMESTAMP_LABEL][0]

    if time_limits is not None:
        position_timestamps = np.array(position_data[TIMESTAMP_LABEL]-first_position_timestamp,\
                dtype=float)/SPIKE_SAMPLING_RATE
        time_limit_start_idx = np.searchsorted(position_timestamps, time_limits[0], side='left')
        time_limit_finish_idx = np.searchsorted(position_timestamps, time_limits[1], side='right')
        position_data = position_data[time_limit_start_idx:time_limit_finish_idx]

    if reset_time:
        position_data[TIMESTAMP_LABEL] = (position_data[TIMESTAMP_LABEL] -
                first_position_timestamp)
    return position_data

def cleanPositionData(position_data):
    """
    Read position data and clean out any jumps or other abnormalities in it.

    :position_data: Position data (raw) read from video-tracking file
    :returns: Cleaned position data.
    """

    raise NotImplementedError()

def getSpikeLocations(spikes, position, speed, speed_threshold=20.0):
    """
    Map spikes to recorded position data.
    INPUTS:
    :spikes: Raw spike-timestamp array, separated by unit IDs
    :position: Raw positon data (should have strictly increasing position timestamps)
    :speed: Speed data (corresponding to the position timestamps)
    :speed_threshold: Lowest speed (in cm/s) for which spike's location should be reported.
    RETURNS:
    :spike_locations: list of spike locations for each cluster passing the speed threshold.
        Each list entry describes the following fields:

                ---------------------------------------------
                |           |          |          |         |
                |   Spike   |    X     |    Y     | Running |
                | Timestamp | Position | Position |  Speed  |
                |           |          |          |         |
                ---------------------------------------------

    """

    if not (np.diff(position[TIMESTAMP_LABEL]) > 0.0).all():
        raise ValueError('Position timestamps have negative jumps!')

    assert(len(position) == len(speed))
    spike_locations = []
    for unit in spikes:
        if unit is None:
            spike_locations.append(None)
            continue

        spike_indices_in_range = np.logical_and(unit > position[TIMESTAMP_LABEL][0], unit < position[TIMESTAMP_LABEL][-1])
        spikes_in_range = unit[spike_indices_in_range]

        # Get the nearest position-value for each spike.
        nearest_position_data = np.searchsorted(position[TIMESTAMP_LABEL], spikes_in_range)
        spike_x_pos = position[X_LOC1_LABEL][nearest_position_data]
        spike_y_pos = position[Y_LOC1_LABEL][nearest_position_data]
        spike_speed = speed[nearest_position_data]
        spikes_passing_threshold = (spike_speed > speed_threshold)

        # Put all the data in a numpy ndarray
        n_spikes_passing_threshold = np.sum(spikes_passing_threshold)
        unit_spike_locations = np.ndarray((n_spikes_passing_threshold, 4), dtype=float)
        unit_spike_locations[:,0] = spikes_in_range[spikes_passing_threshold]
        unit_spike_locations[:,1] = spike_x_pos[spikes_passing_threshold]
        unit_spike_locations[:,2] = spike_y_pos[spikes_passing_threshold]
        unit_spike_locations[:,3] = spike_speed[spikes_passing_threshold]
        spike_locations.append(unit_spike_locations)
    return spike_locations

def loadLFP(data_file=None):
    """
    Load LFP data, test for timestamp jumps.

    :data_file: Location of the LFP data file. Trodes extracted LFP is a .dat file
    :returns: LFP data as a Nx2 array containing LFP timestamps and values
    """

    if data_file is None:
        gui_root = Tk()
        gui_root.wm_withdraw()
        data_file = QtHelperUtils.get_open_file_name(data_dir=DEFAULT_SEARCH_PATH, message="Select LFP data File", \
            file_format="LFP Data (.dat)")
        gui_root.destroy()

    try:
        lfp_data_dict = readTrodesExtractedDataFile3.readTrodesExtractedDataFile(data_file)
        lfp_data = lfp_data_dict['data']
    except (FileNotFoundError, IOError) as err:
        print(err)
        return

    # Look for spike timestamps in the same directory
    timestamps_file = data_file.split('.LFP_')[0] + '.timestamps.dat'
    try:
        lfp_tstamp_dict = readTrodesExtractedDataFile3.readTrodesExtractedDataFile(timestamps_file)
        lfp_tstamps = lfp_tstamp_dict['data']

        if len(lfp_tstamps) == len(lfp_data):
            # Check that the timestamps are uniformly spaced
            tstamp_spacing = np.diff(lfp_tstamps)
            if (tstamp_spacing == tstamp_spacing[0]).all():
                print(MODULE_IDENTIFIER + 'LFP Timestamps uniformly spaced!')
        else:
            print(MODULE_IDENTIFIER + 'LFP Timestamps differ from LFP values in size!')
            lfp_tstamps = None
    except (FileNotFoundError, IOError) as err:
        print(MODULE_IDENTIFIER + 'UNABLE TO READ timestamps file. Using uniformly spaced timestamps!')
        lfp_tstamps = None
    finally:
        return [lfp_tstamps, lfp_data]

if __name__ == "__main__":
    # By default, extract firings into epochs.
    separateSpikesInEpochs()
