from mountainlab_pytools import mdaio
from mountainlab_pytools import mlproc as mlp
import os
import json
import subprocess
import mda_util

# This script acts as the most basic interface between python and mountainlab processors.  
# Defining a processors inputs, outputs, and params here allows processors written in any language
# (as long as they follow mountainlab conventions) to be made into a callable python function with passable params.

# These functions serve as the building blocks for subpipelines, defined in ms4_franklab_pyplines

# In general, each function corresponds to one processor, except in the case where multiple processors always function together 

# Note that NO default params are set here. This is to prevent the use of any default values unknowingly. 
# Default values should be provided in the pyplines script 

#AKGillespie based on code from JMagland   

def read_dataset_params(dsdir):
    params_fname=mlp.realizeFile(dsdir+'/params.json')
    if not os.path.exists(params_fname):
        return {'samplerate':30000.0}
        # raise Exception('Dataset parameter file does not exist: '+params_fname)
    with open(params_fname) as f:
        return json.load(f)
    
def bandpass_filter(*,timeseries,timeseries_out,samplerate,freq_min,freq_max,opts={}):
    return mlp.runProcess(
        'ephys.bandpass_filter',
        {
            'timeseries':timeseries
        },{
            'timeseries_out':timeseries_out
        },
        {
            'samplerate':samplerate,
            'freq_min':freq_min,
            'freq_max':freq_max
        },
        opts
    )

def whiten(*,timeseries,timeseries_out,opts={}):
    return mlp.runProcess(
        'ephys.whiten',
        {
            'timeseries':timeseries
        },
        {
            'timeseries_out':timeseries_out
        },
        {},
        opts
    )

def mask_out_artifacts(*,timeseries,timeseries_out,threshold, interval_size, opts={}):
    return mlp.runProcess(
        'ms3.mask_out_artifacts',
        {
            'timeseries':timeseries
        },
        {
            'timeseries_out':timeseries_out
        },
        {
            'threshold':threshold,
            'interval_size':interval_size
        },
        opts
    )
def ms4alg(*,timeseries,geom,firings_out,detect_sign,adjacency_radius,detect_threshold,opts={}):
    pp={}
    pp['detect_sign']=detect_sign
    pp['adjacency_radius']=adjacency_radius
    pp['detect_threshold']=detect_threshold
    
    return mlp.runProcess(
        'ms4alg.sort',
        {
            'timeseries':timeseries,
            'geom':geom
        },
        {
            'firings_out':firings_out
        },
        pp,
        opts
    )
    
def compute_cluster_metrics(*,timeseries,firings,metrics_out,samplerate,opts={}):
    metrics1=mlp.runProcess(
        'ms3.cluster_metrics',
        {
            'timeseries':timeseries,
            'firings':firings
        },
        {
            'cluster_metrics_out':True
        },
        {
            'samplerate':samplerate
        },
        opts
    )['cluster_metrics_out']

    metrics2=mlp.runProcess(
        'ms3.isolation_metrics',
        {
            'timeseries':timeseries,
            'firings':firings
        },
        {
            'metrics_out':True
        },
        {
            'compute_bursting_parents':'true'
        },
        opts
    )['metrics_out']

    return mlp.runProcess(
        'ms3.combine_cluster_metrics',
        {
            'metrics_list':[metrics1,metrics2]
        },
        {
            'metrics_out':metrics_out
        },
        {},
        opts
    )

# UNTESTED?UNUSED BY AKG
def automated_curation(*,firings,cluster_metrics,firings_out,opts={}):
    # Automated curation
    label_map=mlp.runProcess(
        'ms4alg.create_label_map',
        {
            'metrics':cluster_metrics
        },
        {
            'label_map_out':True
        },
        {},
        opts
    )['label_map_out']
    return mlp.runProcess(
        'ms4alg.apply_label_map',
        {
            'label_map':label_map,
            'firings':firings
        },
        {
            'firings_out':firings_out
        },
        {},
        opts
    )

def tagged_curation(*,cluster_metrics,metrics_tagged,firing_rate_thresh=.01, isolation_thresh=.95, noise_overlap_thresh=.03, peak_snr_thresh=1.5, mv2file='', opts={}):
    # tagged curation
    return mlp.runProcess(
        'pyms.add_curation_tags',
        {
        },
        {
        },
        {
            'metrics':cluster_metrics,
            'metrics_tagged':metrics_tagged,
            'firing_rate_thresh':firing_rate_thresh,
            'isolation_thresh':isolation_thresh, 
            'noise_overlap_thresh':noise_overlap_thresh, 
            'peak_snr_thresh':peak_snr_thresh
        }
    )

def get_epoch_offsets(*,dirnames, dataset_dir, opts={}):
    # Caitlin added dirnames as an input to ensure correct ordering of prv files.
    prv_list = mda_util.get_prv_files_in(dataset_dir,dirnames)
    ep_files = []
    for prv_file in prv_list:
        with open(dataset_dir + '/' + prv_file, 'r') as f:
            ep_files.append(json.load(f))

    # initialize with 0 (first start time)
    lengths = [0]

    for idx, ep_desc in enumerate(ep_files):
        ep_path=ep_desc['original_path']
        ep_mda=mdaio.DiskReadMda(ep_path)
        #get length of the mda (N dimension)
        samplength = ep_mda.N2()
        #add to prior sum and append
        lengths.append(samplength + lengths[(idx)])

    #first entries (incl 0) are starttimes; last is total time
    total_samples =lengths[-1]
    sample_offsets=lengths[0:-1]

    return sample_offsets, total_samples

def pyms_extract_segment(*,timeseries, timeseries_out, t1, t2, opts={}):

    return mlp.runProcess(
        'pyms.extract_timeseries',
        {
            'timeseries':timeseries
        },
        {
            'timeseries_out':timeseries_out
        },
        {
            't1':t1,
            't2':t2
        },
        opts
    )

def pyms_anneal_segs(*,timeseries_list, firings_list, firings_out, dmatrix_out, k1_dmatrix_out, k2_dmatrix_out, dmatrix_templates_out, time_offsets, opts={}):

    return mlp.runProcess(
        'pyms.anneal_segments',
        {
            'timeseries_list':timeseries_list,
            'firings_list':firings_list
        },
        {
            'firings_out':firings_out,
            'dmatrix_out':dmatrix_out,
            'k1_dmatrix_out':k1_dmatrix_out,
            'k2_dmatrix_out':k2_dmatrix_out,
            'dmatrix_templates_out':dmatrix_templates_out
        },
        {
            'time_offsets':time_offsets
        },
        opts
    )

def combine_firing_segs(*,timeseries_list, firings_list, firings_out, dmatrix_out, k1_dmatrix_out, k2_dmatrix_out, dmatrix_templates_out, time_offsets, opts={}):

    return mlp.runProcess(
        'ms3.combine_firing_segments',
        {
            'timeseries_list':timeseries_list,
            'firings_list':firings_list
        },
        {
            'firings_out':firings_out,
            'dmatrix_out':dmatrix_out,
            'k1_dmatrix_out':k1_dmatrix_out,
            'k2_dmatrix_out':k2_dmatrix_out,
            'dmatrix_templates_out':dmatrix_templates_out
        },
        {
            'time_offsets':time_offsets
        },
        opts
    )

def clear_seg_files(*,timeseries_list, firings_list, opts={}):
    for file in timeseries_list:
        os.remove(file)

    for file in firings_list:
        os.remove(file)

      
def pyms_extract_clips(*,timeseries,firings, clips_out,clip_size,opts={}):
    
    return mlp.runProcess(
        'pyms.extract_clips',
        {
            'timeseries':timeseries,
            'firings':firings
        },
        {
            'clips_out':clips_out
        },
        opts
    )
def synthesize_sample_dataset(*,dataset_dir,samplerate=30000,duration=600,num_channels=4,opts={}):
    if not os.path.exists(dataset_dir):
        os.mkdir(dataset_dir)
    M=num_channels
    mlp.runProcess(
        'ephys.synthesize_random_waveforms',
        {},
        {
            'geometry_out':dataset_dir+'/geom.csv',
            'waveforms_out':dataset_dir+'/waveforms_true.mda'
        },
        {
            'upsamplefac':13,
            'M':M,
            'average_peak_amplitude':100
        },
        opts
    )
    mlp.runProcess(
        'ephys.synthesize_random_firings',
        {},
        {
            'firings_out':dataset_dir+'/firings_true.mda'
        },
        {
            'duration':duration
        },
        opts
    )
    mlp.runProcess(
        'ephys.synthesize_timeseries',
        {
            'firings':dataset_dir+'/firings_true.mda',
            'waveforms':dataset_dir+'/waveforms_true.mda'
        },
        {
            'timeseries_out':dataset_dir+'/raw.mda.prv'
        },{
            'duration':duration,
            'waveform_upsamplefac':13,
            'noise_level':10
        },
        opts
    )
    params={
        'samplerate':samplerate,
        'spike_sign':1
    }
    with open(dataset_dir+'/params.json', 'w') as outfile:
        json.dump(params, outfile, indent=4)

def generate_clips_and_features(*, firings, timeseries, label, clip_size=100, num_features=3, subtract_mean=1, opts={}):
    local_firing_out = 'subfirings_'+str(label)+'.out'
    mlp.runProcess(
        'mv.mv_subfirings',
        {
            'firings':firings,
        },{
            'firings_out':local_firing_out
        },{
            'labels':label
        },
        opts
        )
    mlp.runProcess(
        'mv.mv_extract_clips_features',
        {
            'firings':local_firing_out,
            'timeseries':timeseries
        },{
            'features_out':'features'+str(label)+'.out'
        },{
            'clip_size':clip_size,
            'num_features':num_features,
            'subtract_mean':subtract_mean
        },
        opts
        )

def generate_templates_and_amplitudes(*, firings, timeseries, stdevs_out, templates_out, firings_out, clip_size=100, opts={}):
    mlp.runProcess(
        'mv.mv_compute_templates',
        {
            'firings':firings,
            'timeseries':timeseries
        },
        {
            'stdevs_out':stdevs_out,
            'templates_out':templates_out
        },{
            'clip_size':clip_size
        },
        opts
    )
    mlp.runProcess(
        'mv.mv_compute_amplitudes',
        {
            'firings':firings,
            'timeseries':timeseries
        },
        {
            'firings_out':firings_out,
        },{
        },
        opts
    )
