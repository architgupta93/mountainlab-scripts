import os
import sys
import logging
import subprocess
import mda_util
import ms4_franklab_pyplines as pyp
import pyff_utils as pyff
import ms4_franklab_proc2py as p2p
from distutils.dir_util import copy_tree

MODULE_IDENTIFIER = '[MS4Pipeline] '
MDA_UTIL_FILENAME = 'mda_util.py'
PYTHON_EXECUTABLE = 'python3'
PRV_CREAION_EXE   = 'ml-prv-create-index'

def setup_NT_links(working_dir):
    """
    Suppose the day's data are located at /data/path
    For example, the following would already exist for
    animal : JZ1
    date : 20161205
    epochs : 4,5
    tetrodes : 1,2

    <top_level_folder>JZ1_04.mda/20161205_JZ1_nt1.mda
    <top_level_folder>JZ1_04.mda/20161205_JZ1_nt2.mda
    <top_level_folder>JZ1_05.mda/20161205_JZ1_nt1.mda
    <top_level_folder>JZ1_05.mda/20161205_JZ1_nt2.mda
    ...
    and we'd want it to create the following:
    <top_level_folder>JZ1.mountain/nt1/4/raw.mda.prv
    <top_level_folder>JZ1.mountain/nt1/5/raw.mda.prv
    <top_level_folder>JZ1.mountain/nt2/4/raw.mda.prv
    <top_level_folder>JZ1.mountain/nt2/5/raw.mda.prv
    ...
    """

    # TODO: Implement this function when we are working with multiple epochs.
    mda_util.make_sure_path_exists(working_dir+'mountain')
    raw_data_dir = working_dir + '/raw'
    for tet_dir in os.listdir(raw_data_dir):
        # subprocess.call([PRV_CREAION_EXE, tet_dir, raw_data_dir])
    pass


def run_franklab_pipeline(source_dir, results_dir=None, animal_name=None):
    # Get the path for this file -> And then the directory in which this file
    # is located. We do expect mda_utils to be in the same location as this
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    mda_util_path = current_file_dir + '/' + MDA_UTIL_FILENAME
    if results_dir is None: 
        results_dir= current_file_dir + '/' + 'results/'

    if animal_name is None:
        animal_name = input("Input Name/ID for the animal... ")

    mnt_path = results_dir + '.mnt/'
    raw_mnt_path = mnt_path + 'raw'
    print('Processing ' + source_dir)
    try:
        if not os.path.exists(mnt_path):
            print('No mnt directory found; Calling mda_util')
            mda_util.make_mda_ntrodeEpoch_links([source_dir], raw_mnt_path)
    except Exception as err:
        print("MDA Utils failed to run. Cannot create appropriate softlinks. Aborting!")
        print(err)
        return

    print('MDA Util Ran successfully')
    mountain_src_path = mnt_path + '/mountain'
    mountain_res_path = results_dir + '/preprocessing/' + '.mountain'
    
    print('Source ' + mountain_src_path)
    print('Destination ' + mountain_res_path)
    if not os.path.exists(mountain_src_path):
        print('No mountain dir found; setting up links across epochs...')
        setup_NT_links(mnt_path)
    print('Finished creating NT Links')
    if not os.path.exists(mountain_res_path):
        try:
            print('Copying Mountain dir to Results dir')
            copy_tree(mountain_src_path, mountain_res_path)
        except Exception as err:
            print("Unable to copy directory tree...")
            print(err)
            return
    else:
        print(mountain_res_path + ' Exists!')

    nt_ind = 0
    nt = 2
    nt_src_dir = mountain_src_path+'/nt'+str(nt)
    nt_out_dir = mountain_res_path+'/nt'+str(nt)
    
    # concatenate all eps, since ms4 no longer takes a list of mdas; save as raw.mda
    # save this to the output dir; it serves as src for subsequent steps
    prv_list=nt_src_dir+'/raw.mda.prv'
    print('Calling concat_eps')
    print()
    pyp.concat_eps(dataset_dir=nt_out_dir, mda_list=prv_list)
    
    # preprocessing: filter, mask out artifacts, whiten
    # TODO make optional whether you save the interediates (filt, pre)
    pyp.filt_mask_whiten(dataset_dir=nt_out_dir,output_dir=nt_out_dir, freq_min=300,freq_max=6000, opts={})
    
    #run the actual sort 
    pyp.ms4_sort_on_segs(dataset_dir=nt_out_dir,output_dir=nt_out_dir, adjacency_radius=-1,detect_threshold=3, detect_sign=-1, opts={})
    nt_dir = mountain_path+'/nt'+str(nt)
    pyp.add_curation_tags(dataset_dir=nt_dir,output_dir=nt_dir,opts={})
    pyp.extract_marks(dataset_dir=nt_dir,output_dir=nt_dir,opts={})

if __name__ == "__main__":
    dirnames = []
    resname = None
    try:
        result_dir = sys.argv[1]
        source_dir = sys.argv[2]
        run_franklab_pipeline(source_dir, result_dir)
    except Exception as err:
        print(MODULE_DENTIFIER + "Expecting source/destination directories")
        print(MODULE_DENTIFIER + "Usage python MS4batch.py <target> <sources>")
        print(err)
