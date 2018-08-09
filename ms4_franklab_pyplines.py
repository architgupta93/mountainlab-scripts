#from mountainlab_pytools import mdaio
#from mountainlab_pytools import mlproc as mlp
import os
import json
import subprocess
import ms4_franklab_proc2py as p2p
import math

# This script calls the helper functions defined in p2p that in turn, call MS processors
# This should be a collection of common processing steps that are standard across the lab, altho params can be changed flexibly
# Default params are defined in the arguments of each pypline, but can be overwritten by the user 

# These pyplines should be called by a python batch script, which will manage running the steps on particular animal, days, and ntrodes
# AKGillespie based on code from JMagland 

#before anything else, must concat all eps together becuase ms4 no longer handles the prv list of mdas
def concat_eps(*,dataset_dir, mda_list,opts={}):

    with open(mda_list) as f:
        mdalist=json.load(f)

    strstart = []
    for entries in mdalist['files']:
        strstart.append('timeseries_list:'+entries['prv']['original_path'])
    
    joined = ' '.join(strstart)

    outpath = 'timeseries_out:'+dataset_dir+'/raw.mda'
    subprocess.call(['ml-run-process','ms3.concat_timeseries','--inputs',joined,'--outputs',outpath])                    
    #somehow turn list of files into dictionary 



def filt_mask_whiten(*,dataset_dir,output_dir,freq_min=300,freq_max=6000,mask_artifacts=1,opts={}):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
        
    # Dataset parameters
    ds_params=p2p.read_dataset_params(dataset_dir)
    
    # Bandpass filter
    p2p.bandpass_filter(
        timeseries=dataset_dir+'/raw.mda',
        timeseries_out=output_dir+'/filt.mda.prv',
        samplerate=ds_params['samplerate'],
        freq_min=freq_min,
        freq_max=freq_max,
        opts=opts
    )
    # Mask out artifacts
    if mask_artifacts:
        p2p.mask_out_artifacts(
            timeseries=output_dir+'/filt.mda.prv',
            timeseries_out=output_dir+'/filt.mda.prv',
            threshold = 5,
            interval_size=2000,
            opts=opts
            )
    # Whiten
    p2p.whiten(
        timeseries=output_dir+'/filt.mda.prv',
        timeseries_out=output_dir+'/pre.mda.prv',
        opts=opts
    )
    
    
# full = sort the entire file as one mda
def ms4_sort_full(*,dataset_dir, output_dir, geom=[], adjacency_radius=-1,detect_threshold=3,detect_sign=0,opts={}):

    # Fetch dataset parameters
    ds_params=p2p.read_dataset_params(dataset_dir)


    p2p.ms4alg(
        timeseries=output_dir+'/pre.mda.prv',
        geom=geom,
        firings_out=output_dir+'/firings_raw.mda',
        adjacency_radius=adjacency_radius,
        detect_sign=detect_sign,
        detect_threshold=detect_threshold,
        opts=opts
    )
    
    # Compute cluster metrics
    p2p.compute_cluster_metrics(
        timeseries=output_dir+'/pre.mda.prv',
        firings=output_dir+'/firings_raw.mda',
        metrics_out=output_dir+'/metrics_raw.json',
        samplerate=ds_params['samplerate'],
        opts=opts
    )
    

# segs = sort by timesegments, then join any matching  clusters
def ms4_sort_on_segs(*,dataset_dir, output_dir, geom=[], adjacency_radius=-1,detect_threshold=3,detect_sign=0,rm_segment_intermediates=1, opts={}):

    # Fetch dataset parameters
    ds_params=p2p.read_dataset_params(dataset_dir)

    # calculate time_offsets and total_duration
    sample_offsets, total_samples = p2p.get_epoch_offsets(dataset_dir=dataset_dir)

    #break up preprocesed data into segments and sort each 
    firings_list=[]
    timeseries_list=[]
    for segind in range(len(sample_offsets)):
        t1=math.floor(sample_offsets[segind]) 
        if segind==len(sample_offsets)-1:
            t2=total_samples-1
        else:
            t2=math.floor(sample_offsets[segind+1])-1 

        segment_duration = t2-t1
        print('Segment '+str(segind+1)+': t1='+str(t1)+', t2='+str(t2)+', t1_min='+str(t1/ds_params['samplerate']/60)+', t2_min='+str(t2/ds_params['samplerate']/60));

        pre_outpath= dataset_dir+'/pre-'+str(segind+1)+'.mda'
        p2p.pyms_extract_segment(
            timeseries=output_dir+'/pre.mda.prv', 
            timeseries_out=pre_outpath, 
            t1=t1, 
            t2=t2,
            opts=opts)

        firings_outpath=dataset_dir+'/firings-'+str(segind+1)+'.mda'
        p2p.ms4alg(
            timeseries=pre_outpath,
            firings_out=firings_outpath,
            geom=geom,
            detect_sign=detect_sign,
            adjacency_radius=adjacency_radius,
            detect_threshold=detect_threshold,
            opts=opts)

        firings_list.append(firings_outpath)
        timeseries_list.append(pre_outpath)

    firings_out_final=output_dir+'/firings_raw.mda'
    p2p.pyms_anneal_segs(
        timeseries_list=timeseries_list, 
        firings_list=firings_list,
        firings_out=firings_out_final,
        dmatrix_out=[],
        k1_dmatrix_out=[],
        k2_dmatrix_out=[],
        dmatrix_templates_out=[],
        sample_offsets=sample_offsets
    )
    
    # clear the temp pre and firings files if specified
    if rm_segment_intermediates:
        p2p.clear_seg_files(
            timeseries_list=timeseries_list, 
            firings_list=firings_list
        )

    # Compute cluster metrics
    p2p.compute_cluster_metrics(
        timeseries=output_dir+'/pre.mda.prv',
        firings=output_dir+'/firings_raw.mda',
        metrics_out=output_dir+'/metrics_raw.json',
        samplerate=ds_params['samplerate'],
        opts=opts
    )
    

def add_curation_tags(*, dataset_dir, output_dir, opts={}):
    # note that this is split out and not included after metrics calculation
    # because of a bug in ms3.combine_cluster_metrics - doesn't work if anything follows it

    p2p.tagged_curation(
        cluster_metrics=dataset_dir+'/metrics_raw.json',
        metrics_tagged=output_dir+'/metrics_raw.json',
        firing_rate_thresh=.01, 
        isolation_thresh=.95, 
        noise_overlap_thresh=.03, 
        peak_snr_thresh=1.5, 
        mv2file=[],
        opts=opts
    ) 

def extract_clips(*,dataset_dir, output_dir, clip_size):

    p2p.pyms_extract_clips(
        timeseries=dataset_dir+'/pre.mda.prv',
        firings=dataset_dir+'/firings_raw.mda',
        clips_out=output_dur+'/clips.mda',
        clip_size=clip_size,
        opts=opts)

def extract_marks(*,dataset_dir, output_dir):

    p2p.pyms_extract_clips(
        timeseries=dataset_dir+'/pre.mda.prv',
        firings=dataset_dir+'/firings_raw.mda',
        clips_out=output_dur+'/marks.mda',
        clip_size=1,
        opts=opts)