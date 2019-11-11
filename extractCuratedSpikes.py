import os
import sys
import json

# Mountainlab tools
from mountainlab_pytools import mdaio

# Parameter definitions. Tweak to get your desired cluster selection
PEAK_AMPLITUDE_LO_CUTOFF = 5.0      # MIN value of peak amplitude
PEAK_AMPLITUDE_HI_CUTOFF = 100.0    # MAX value of peak amplitude (Handy for cleaning artifacts)
ISOLATION_THRESHOLD      = 0.90
PEAK_SNR_CUTOFF          = 3.0

MODULE_IDENTIFIER        = "[AutoCuration] "

def autocurate(firings_file='firings_raw.mda', metrics_file='metrics_cleaned.json', \
        output_file='firings_autocurated.mda')
    """
    Load raw firings from file and use metrics to automatically curate them.
    """

    # Load the metrics file and identify the clusters that need to be retained
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
        if (cluster['metrics']['peak_amp'] is None) or (cluster['metrics']['peak_snr'] is None):
            continue

        if (cluster['metrics']['peak_amp'] > PEAK_AMPLITUDE_HI_CUTOFF) or \
                (cluster['metrics']['peak_amp'] < PEAK_AMPLITUDE_LO_CUTOFF):
            continue

        if (cluster['metrics']['isolation'] < ISOLATION_THRESHOLD):
            continue

        if cluster['metrics']['peak_snr'] < PEAK_SNR_CUTOFF:
            continue

        # If none of the stuff above eats through the metrics, the cluster is accepted
        accepted_clusters[cluster['label']] = True
    print(MODULE_IDENTIFIER + "Processed clusters. Accepted following...")
    print(accepted_clusters)

    try:
        firing_data = mdaio.readmda(firings_filename)
        n_spikes = firing_data.shape[1]
        acceptance_mask = np.zeros(n_spikes, dtype='bool')
        for spk_idx, spk_cl in firing_data[2,:]:
            acceptance_mask[spk_idx] = accepted_clusters[spk_cl]

        mdaio.writemda64(firing_data[:, acceptance_mask], output_file)
    except (FileNotFoundError, IOError) as err:
        QtHelperUtils.display_warning('Unable to read MDA file.')
        print(err)
        return

if __name__ == "__main__":
    pass
