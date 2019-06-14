# FosterLab MountainSort pipeline
## This repo contains python packages (MLView, MS4batch) for managing mountainsort processing. It has been built o n top of Frank Lab's processing pipelines.
MS4 batch relies on pyplines: collections of processors that perform a collective function, such as preprocessing. 
pyplines contains calls to the helper module proc2py, which serves as an interface to make processors written in any language callable in python. 

## This system has been built using the MS4 (mountainlab-js) conda package. 
It also makes use of the following accessory processors:
	msdrift: https://bitbucket.org/franklab/franklab_msdrift/src/master/ 
	ms_tagged_curation: https://bitbucket.org/franklab/franklab_mstaggedcuration/src/master/ 
Place symlinks to these repos in the /etc/mountainlab/packages directory of your conda environment

# Guide to Mountainsort 
(as the frank lab uses it)

## Installing mountainsort:
The long (and possibly better) way of installing mountainsort can be found on the official website.
Follow the instructions for conda installation here: https://github.com/flatironinstitute/mountainlab-js. I have a compact set of instructions in the file 0-mountainlab-readme which used to work at one point. I am not entirely sure if it would still work after the recent changes to mountainsort (as of writing this on June 13, 2019).

ALTERNATIVELY, run the following hack to install mountainsort:
    $ conda create -n mlab --file mountainlab.env.info

Subsitute mlab with any name that you would like for your mountainlab environment. mountainlab.env.info has a list of packages and package version that were all compatible with mountainsort at some point and can be used to run spike sorting.
After this, we need to update a few packages and test that everything is working.

    $ conda activate mlab
    $ conda install -c flatiron ml_ephys

## Component Details
prv: This is a json file (created by jeremy) that acts as a pointer (like an address book) to other files. MS uses it in many instances to keep track of large source data files (or processed files in the tmp directory) rather than storing copies of these big files in multiple locations.  PRVs locate data files by their checksum, a unique identifier based on the content of the file. (This can be found for any file by using the sha1sum command in a terminal)

Mda_util.py: This makes the .mnt directory and its contents, containing symbolic links to the mda files for each epoch for each ntrode. We use this because our raw data is stored by epoch, with all tets in subfolders. Since we generally want to sort across all the epochs in a day, this tool reorganizes the data so that it is first grouped by tetrode, then epoch. This is all done with symlinks, so no duplicate files are generated 

Setup_ntlinks.node.js: This creates the .mountain directory, which creates the raw.mda.prv for each ntrode, telling mountainsort where to find the data from each epoch for that ntrode. (see above for a PRV explanation)

MS4batch.ipynb: notebook for managing your sort at the highest level - specifying animals, days, and tets and the pipelines to run on them.

ms4_franklab_pyplines.py: module containing pipelines that group processors in logical functions, such as preprocess (filter/mask/whiten) and sort

ms4_franklab_proc2py.py: module containing functions that serve as an interface to make processors written in any language callable in python.

pyff_utils.py: handy functions that are the early stages of filterframework getting translated from matlab into python (franklab-specific)

## Inputs to MS
Raw.mda.prv: points to each epoch’s worth of data for that ntrode
Params.json: contains information about the parameters to use for the sort. These can be overwritten by specifying them in the call to run the sort (in the batch script)
Geom.csv (optional): contains information about the location of contacts for that ntrode; used in concert with adjacency_radius to determine the neighborhoods to sort on. In the case of tetrodes, this is not necessary because all the contacts of a tetrode should be sorted together as a single neighborhood. This can be specified by not providing a geom.csv, setting adjacency_radius to -1, or both.

## Sorting parameters
These are set as defaults in the pyplines module, but can also be passed in as arguments to the sort call, i.e. --detect_sign = -1.

- detect_sign: the direction of spike to detect (-1 for negative, 1 for positive, 0 for both).  -1 is recommended for most recordings.  

- detect_interval: minimum distance apart in samples that two spikes must be to both be detected. (default 10)

- detect_threshold: spike detection threshold in standard deviations (default 3)

- samplerate: the recording sample rate in Hz
	
- freq_min: the highpass or low cutoff of the filter (default 300 Hz)

- freq_max: the lowpass or high cutoff of the filter (default 6000 Hz)
	
- clip_size: the size of extract clips around each spike, in samples (default 50)
	
- adjacency_radius: the radius in µm that defines a neighborhood of channels on which to sort (default -1 to ignore and not require a geom.csv file, useful for tetrodes)

## Outputs from MS
- Firings_raw.mda: this contains the actual spike timing info that you care most about [electrode;time;label x #events….] for ALL detected events, regardless of cluster quality

- Firings_curated.mda: this contains spike timing info for the events that pass cluster curation criteria DEPRECATED

- Pre.mda (optional) if you choose to save it, this contains the filtered and whitened data. If you have the space, its useful to save this and feed it into mountainview to visualize your clusters (otherwise it just takes a while to recompute it)

- Filt.mda (optional) this contains the filtered data, which like the pre, can be helpful to feed into mountainview for visualization.  Firings events and spike spray are best visualized with filtered data.

- Metrics_raw.mda: metrics for all the original clusters

- Metrics_curated.json : this contains the metrics for the curated clusters, such as isolation scores, noise overlap, SNR, and more

- Firings_processed.mda: contains all spikes from all clusters after any merges have been done

- Metrics_processed.mda: contains metrics post merge and including any tags (either from automatic curation tagging or manual tagging)

- Mv2 file: saves any cluster labels that you have assigned in mountainview. Also useful for keeping track of tags and reassigning them post-merging recalculation of metrics

## Running your own sort: walking through the steps of the batch notebook
### Run mda_util.py and setup javascript (spefific for frank lab data organization)
NOTE: will have to change permissions to make it executable

This creates the symbolic links to the .mda files for all epochs for each ntrode within an .mnt directory

The setup javascript sets up the directory structure and the symbolic links (.prv files) that tell mountainsort where to find the data for each epoch for each ntrode. 

This is run from inside the day directory that you want to process and specify the .mnt directory. 

Currently this is made lightly more cumbersome (but useful) by the ability to save the intermediate files and results to a different location than where the original mda data is stored 

### Concatenate any epochs that you want to sort together
In contrast to MS3 and earlier, MS4 no longer takes a prv containing a directory's worth of files as an input. so, you have to create the concatenated mda to work off.

### Preprocess your data
Filter, mask out artifacts, and whiten the data, and save the output as pre. Defaults for the filter band can be passed in, as can the amplitude and duration of events detected as artifacts. It is useful to save the filtered data also for later viewing in mountainview. 

### Sort the data using ms4 algorithm
2 common options for your sort:
1. Sort_full: sort the whole chunk of data togther. 

2. Sort_on_segments: what we refer to when we say we're using the drift tracking pipeline. This runs the sort on chunks of the full data (commonly epochs, but this is flexible) and then matches up any clusters that are continuos across epochs. Clusters that do not match clusters in other epochs will be retained, but only present in those specific epochs. This allows you to capture clusters that might drift or change over the span of the recorded data. Note that optimal cluster metrics calculation for this method are still under development

For either options, metrics for your resultant clusters will also be calculated. 

### Curate your sort results
2 options:
1. Automatic curation: this applies curation criteria to your clusters, automatically merges burst parents, and rejects clusters that do not meet curation thresholds 

2. Tagged curation: This labels any clusters that do not meet curation criteria as MUA, but keeps them around for inspection. It does not merge burst parents by default.
	
### Inspect your results in mountainview
launch mountainview from the terminal and point it to your data:
mountainview --pre=pre.mda --firings=firings.mda --samplerate=30000 --cluster_metrics=metrics_raw.json

Note that some views make most sense for particular types of data : use filtered data to view cluster detail (to make sense of waveform shape) and spike spray; use filtered&whitened for PCA, amplitude histograms, and discrimination histograms. Don’t really use raw data for anything.

Key things to check:
- Make sure all autocorrelograms have the nice dip in the center. If there’s no dip in the center, it’s definitely not a single unit (all cells must have a refractory period of at least 1ms!). BUT just because it has a clean gap doesn’t mean it HAS to be a single unit (cells, esp place cells, will not fire at the same time as other place cells because they’ll be isolated in space and in theta phase)

- Make sure that the amplitude histograms are not cut off by the detection threshold - you only want ones with a nice complete distribution

- Check the crosscorrelograms and make sure that none are super correlated - this is usually well taken care of already by bursting parent merging

- Take a closer look at any clusters that are close to the isolation cutoff (.95-.97) - these are the ones that may be multiunit. If this is the case, they probably also are small (peak amp <10) and have low SNR (<2.5). These should be rejected unless you are interested in using them for multi
	
- Use the firing events view to assess stability - if something drifts around a ton, it may not be very reliable

- Check suggested burst parent pairs; merge if  they look reasonable

Save your manually verified results! 

1. Make any merges permanent by using the export curated firings button to save a firings_processed.mda 

	NOTE THAT the export curated firings button ignores anything tagged as rejected, but we actually want to keep all the mua/rejected clusters around! SO, tag any non-single-units as mua or noise, but not rejected. Keeping rejected clusters around is important because when/if you merge clusters and thus need to recalculate metrics, you need to do this in relation to ALL events, not just the accepted clusters.

	The export firings button does not preserve merges. 

2. Use the export cluster metrics button to save a metrics_processed.json

3. Use the export mv2 button to save a manualcuration.mv2 (or whatever you want to call it) - this is useful because it will save (and carry over) your tags when/if you recalculate metrics postmerge (see below)
