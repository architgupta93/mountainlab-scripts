import os
import sys
import json
import numpy as np

# Mountainlab tools
from mountainlab_pytools import mdaio

# Local imports
import QtHelperUtils
import MountainViewIO

# Parameter definitions. Tweak to get your desired cluster selection
PEAK_AMPLITUDE_LO_CUTOFF = 5.0      # MIN value of peak amplitude
PEAK_AMPLITUDE_HI_CUTOFF = 100.0    # MAX value of peak amplitude (Handy for cleaning artifacts)
ISOLATION_THRESHOLD      = 0.90
PEAK_SNR_CUTOFF          = 3.0
NOISE_OVERLAP_CUTOFF     = 0.25

MODULE_IDENTIFIER        = "[AutoCuration] "
FIRINGS_FILENAME         = '/firings_raw.mda'
METRICS_FILENAME         = '/metrics_cleaned.json'
OUTPUT_FILENAME          = '/firings_autocurated.mda'
def autocurate(firings_file, metrics_file, output_file):
    """
    Load raw firings from file and use metrics to automatically curate them.
    """

    # Load the metrics file and identify the clusters that need to be retained
    print(MODULE_IDENTIFIER + "Reading metrics file")
    try:
        with open(metrics_file, 'r') as f:
            metrics = json.load(f)
    except (FileNotFoundError, IOError) as err:
        print('ERROR: Unable to read metrics file. Aborting.')
        print(err)
        return

    accepted_clusters = dict()
    for cluster in metrics['clusters']:
        accepted_clusters[cluster['label']] = False
        if (cluster['metrics']['peak_amp'] is None) or \
                (cluster['metrics']['peak_snr'] is None) or \
                (cluster['metrics']['noise_overlap'] is None):
            continue

        if (cluster['metrics']['peak_amp'] > PEAK_AMPLITUDE_HI_CUTOFF) or \
                (cluster['metrics']['peak_amp'] < PEAK_AMPLITUDE_LO_CUTOFF):
            continue

        if (cluster['metrics']['isolation'] < ISOLATION_THRESHOLD):
            continue

        if cluster['metrics']['peak_snr'] < PEAK_SNR_CUTOFF:
            continue

        if cluster['metrics']['noise_overlap'] > NOISE_OVERLAP_CUTOFF:
            continue

        # If none of the stuff above eats through the metrics, the cluster is accepted
        accepted_clusters[cluster['label']] = True

    print(MODULE_IDENTIFIER + "Processed clusters. Accept/Reject decisions...")
    print(accepted_clusters)

    try:
        firing_data = mdaio.readmda(firings_file)
        n_spikes = firing_data.shape[1]
        acceptance_mask = np.zeros(n_spikes, dtype='bool')
        for spk_idx in range(n_spikes):
            acceptance_mask[spk_idx] = accepted_clusters[firing_data[2,spk_idx]]

        mdaio.writemda64(firing_data[:, acceptance_mask], output_file)
        print(MODULE_IDENTIFIER + "Read %d spikes in raw file."%n_spikes)
        print(MODULE_IDENTIFIER + "%d accepted spikes written to %s."%(np.sum(acceptance_mask), output_file))
    except (FileNotFoundError, IOError) as err:
        QtHelperUtils.display_warning('Unable to read/write MDA file.')
        print(err)
        return

if __name__ == "__main__":
    parsed_arguments = QtHelperUtils.parseQtCommandlineArgs(sys.argv)
    data_dir = os.getcwd()
    if parsed_arguments.data_dir:
        data_dir = parsed_arguments.data_dir

    output_dir = data_dir
    if parsed_arguments.output_dir:
        output_dir = parsed_arguments.output_dir

    # Get a list of all the tetrode directories
    for nt_dir in os.listdir(data_dir):
        # Check if the output directory does not exist.
        out_nt_dir = os.path.join(output_dir, nt_dir)
        if not os.path.exists(out_nt_dir):
            print(MODULE_IDENTIFIER + "Output directory %s not found. Creating...")
            os.mkdir(out_nt_dir)
        autocurate(os.path.join(data_dir, nt_dir + FIRINGS_FILENAME), \
                os.path.join(data_dir, nt_dir + METRICS_FILENAME), \
                os.path.join(output_dir, nt_dir + OUTPUT_FILENAME))
        print(MODULE_IDENTIFIER + "Finished %s"%nt_dir)

