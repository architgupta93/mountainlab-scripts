import os
import sys
import json
import logging
import shutil
import subprocess
import commandline
import mda_util
import ms4_franklab_pyplines as pyp
import ms4_franklab_proc2py as p2p
from distutils.dir_util import copy_tree
from shutil import move
from tkinter import Tk, filedialog

MODULE_IDENTIFIER = '[MS4Pipeline] '
MDA_UTIL_FILENAME = 'mda_util.py'
PYTHON_EXECUTABLE = 'python3'
PRV_CREAION_EXE   = 'ml-prv-create-index'
RAW_DIR_NAME      = '/raw'
MOUNTAIN_DIR_NAME = '/mountain'
ML_PRV_CREATOR    = 'ml-prv-create'
ML_TMP_DIR        = '/tmp/mountainlab-tmp'

def relocate_mda(prv_file, target_directory):
    """
    Look at a PRV file, identify the MDA location and move it to the specified
    target location.
    """
    try:
        with open(prv_file) as f:
            prv_data = json.load(f)
        mda_path = prv_data['original_path']
        raw_filename = mda_path.split('/')[-1]
        print('Copying MDA from %s.'%mda_path)
        dest_filename = target_directory + '/' + raw_filename
        shutil.move(mda_path, dest_filename)
        os.symlink(dest_filename, mda_path)
    except (FileNotFoundError, IOError) as err:
        print('Unable to copy original MDA to output directory.')
        print(err)

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
    mnt_data_dir = working_dir + MOUNTAIN_DIR_NAME
    raw_data_dir = working_dir + RAW_DIR_NAME
    mda_util.make_sure_path_exists(mnt_data_dir)
    for tet_dir in os.listdir(raw_data_dir):
        destlink = mnt_data_dir + '/' + tet_dir
        srclink  = raw_data_dir + '/' + tet_dir
        mda_util.make_sure_path_exists(destlink)
        print("Linking " + tet_dir)
        for mda_idx, mda_file in enumerate(os.listdir(srclink)):
            mda_file_path = srclink + '/' + mda_file
            mda_file_name = mda_file.strip('.mda')
            output_file_path = destlink + '/' + mda_file_name + '.raw.mda.prv'
            subprocess.call([ML_PRV_CREATOR, mda_file_path, output_file_path])

def run_pipeline(source_dirs, results_dir):
    # Get the path for this file -> And then the directory in which this file
    # is located. We do expect mda_utils to be in the same location as this
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    mda_util_path = current_file_dir + '/' + MDA_UTIL_FILENAME
    mnt_path = results_dir + '.mnt'
    raw_mnt_path = mnt_path + '/raw'
    print('Processing ' + ', '.join(source_dirs))

    try:
        if not os.path.exists(mnt_path):
            print('No mnt directory found; Calling mda_util')
            mda_util.make_mda_ntrodeEpoch_links(source_dirs, raw_mnt_path)
    except (FileNotFoundError, IOError) as err:
        print("MDA Utils failed to run. Cannot create appropriate softlinks. Aborting!")
        print(err)
        return

    print('MDA Util Ran successfully')
    mountain_src_path = mnt_path + '/mountain'
    mountain_res_path = mnt_path + '/preprocessing'
    
    print('Source ' + mountain_src_path)
    print('Destination ' + mountain_res_path)
    if not os.path.exists(mountain_src_path):
        print('No mountain dir found; setting up links across epochs...')
        setup_NT_links(mnt_path)
    print('Finished creating NT Links')
    if not os.path.exists(mountain_res_path):
        os.mkdir(mountain_res_path)
    else:
        print(MODULE_IDENTIFIER + mountain_res_path + ' Exists!')

    # Create a timeseries directory for storing all the timeseries data generated
    mountainlab_tmp_path = mnt_path + '/mountainlab-tmp'
    if not os.path.exists(mountainlab_tmp_path):
        os.mkdir(mountainlab_tmp_path)
    templates_directory = mountainlab_tmp_path + '/tmp_long_term'
    if not os.path.exists(templates_directory):
        os.mkdir(templates_directory)

    tetrode_list = range(1,2)
    for nt in tetrode_list:
        nt_src_dir = mountain_src_path+'/nt'+str(nt)
        nt_out_dir = mountain_res_path+'/nt'+str(nt)
        mda_util.make_sure_path_exists(nt_out_dir)

        # concatenate all eps, since ms4 no longer takes a list of mdas; save as raw.mda
        # save this to the output dir; it serves as src for subsequent steps
        prv_list=mda_util.get_prv_files_in(nt_src_dir)
        print('Concatenating Epochs: ' + ', '.join(prv_list))

        if not os.path.isfile(nt_out_dir + pyp.CONCATENATED_EPOCHS_FILE):
            pyp.concat_eps(dataset_dir=nt_src_dir, output_dir=nt_out_dir, prv_list=prv_list)
        else:
            print(MODULE_IDENTIFIER + "Raw file with concatenated epochs found. Using file!")
        
        # preprocessing: filter, mask out artifacts, whiten
        move_filt_mask_whiten_files = False
        if not (os.path.isfile(nt_out_dir + pyp.FILT_FILENAME) and os.path.isfile(nt_out_dir + pyp.PRE_FILENAME)):
            pyp.filt_mask_whiten(dataset_dir=nt_out_dir,output_dir=nt_out_dir, freq_min=300,freq_max=6000, opts={})
            relocate_mda(nt_out_dir + pyp.FILT_FILENAME, mountainlab_tmp_path)
            relocate_mda(nt_out_dir + pyp.MASK_FILENAME, mountainlab_tmp_path)
            move_filt_mask_whiten_files = True
        else:
            print(MODULE_IDENTIFIER + "Filt file with concatenated epochs found. Using file!")
        
        #run the actual sort 
        if not (os.path.isfile(nt_out_dir + pyp.FIRINGS_FILENAME) and os.path.isfile(nt_out_dir + pyp.RAW_METRICS_FILE)):
            pyp.ms4_sort_on_segs(dataset_dir=nt_src_dir,output_dir=nt_out_dir, adjacency_radius=-1,detect_threshold=3, detect_sign=-1, opts={})
        else:
            print(MODULE_IDENTIFIER + "Firings and raw cluster metrics file with concatenated epochs found. Using file!")

        if not os.path.isfile(nt_out_dir + pyp.TAGGED_METRICS_FILE):
            pyp.add_curation_tags(dataset_dir=nt_out_dir,output_dir=nt_out_dir,opts={})
        else:
            print(MODULE_IDENTIFIER + "Tagged cluster metrics file with concatenated epochs found. Using file!")

        if not os.path.isfile(nt_out_dir + pyp.CLIPS_FILE):
            pyp.extract_marks(dataset_dir=nt_out_dir,output_dir=nt_out_dir,opts={})
        else:
            print(MODULE_IDENTIFIER + "Clips file with concatenated epochs found. Using file!")

        pyp.cleanup_metrics(metrics_file=nt_out_dir+'/metrics_tagged.json', metrics_out=nt_out_dir+'/metrics_cleaned.json')
        # Generate templates for MountainView
        if not (os.path.isfile(nt_out_dir + pyp.TEMPLATES_FILE) and
                os.path.isfile(nt_out_dir + pyp.TEMPLATE_STDS_FILE) and
                os.path.isfile(nt_out_dir + pyp.AMPLITUDES_FILE)):
            pyp.generate_templates(dataset_dir=nt_out_dir, output_dir=nt_out_dir, metrics_file=nt_out_dir+'/metrics_cleaned.json', opts={})
        else:
            print(MODULE_IDENTIFIER + "Templates file found. Using file!")

        if (os.path.isfile(nt_out_dir + '/hand_curated.json')):
            pyp.add_curation_tags(dataset_dir=nt_out_dir,output_dir=nt_out_dir, hand_curation=True)

        if move_filt_mask_whiten_files:
            relocate_mda(nt_out_dir + pyp.PRE_FILENAME, mountainlab_tmp_path)


if __name__ == "__main__":
    commandline_args = commandline.parse_commandline_arguments()
    if not commandline_args.output_dir:
        print(MODULE_IDENTIFIER + "Using working directory for storing sorted spikes and softlinks.")
        commandline_args.output_dir = os.getcwd() + '/' + commandline_args.animal + str(commandline_args.date)

    # Get source directories using file dialogs.
    gui_root = Tk()
    gui_root.wm_withdraw()
    mda_list = []
    """
    # NOTE: This does not work because top-level MDA files end up being directories
    filenames = filedialog.askopenfilenames(initialdir=os.getcwd(), title="Select MDA Files", \
            filetypes=(("MDA files", ".mda"), ("All Files", "*.*")))
    """
    if commandline_args.data_dir:
        initial_directory = commandline_args.data_dir
    else:
        print("Using root directory as start-point for MDA search.")
        initial_directory = '/'

    while True:
        new_mda_dir = filedialog.askdirectory(initialdir=initial_directory, \
                title="Select MDA Files")
        if not new_mda_dir:
            break
        mda_list.append(new_mda_dir)
        print("Added %s."%new_mda_dir)
    gui_root.destroy()

    run_pipeline(mda_list, commandline_args.output_dir)
