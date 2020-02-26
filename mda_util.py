#!/usr/bin/python3
#run this from the preprocessing directory containing all dates' data
import os
import sys
import json
import shutil
import threading

MODULE_IDENTIFIER = "[MDA Linker] "
MDA_EXTENSION = '.mda'
TETRODE_EXTENSION = '.nt'

def clear_mda(prv_file):
    """
    Look at a PRV file and delete the corresponding MDA.
    """
    try:
        with open(prv_file) as f:
            prv_data = json.load(f)
        mda_path = prv_data['original_path']
        raw_filename = mda_path.split('/')[-1]
        print('Copying MDA from %s.'%mda_path)
        os.remove(mda_path)
        os.remove(prv_file)
    except (FileNotFoundError, IOError) as err:
        print('Unable to remove original MDA.')
        print(err)

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

class MDAReallocator(threading.Thread):
    """
    MDA files are typically very large and moving them can be very time
    consuming. We can initialize threads that take care of this file movement,
    improving the overall runtime for our sorting. Since this is file IO, this
    might also be suitable for python threading class.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True

def get_prv_files_in(dataset_dir='./'):
    """
    Get all the prv files in the directory specified by dataset_dir
    """
    prv_files = []
    all_files = os.listdir(dataset_dir)
    for f in all_files:
        if f.endswith('.prv'):
            prv_files.append(f)
    return prv_files

def make_mda_ntrodeEpoch_links(dirnames=[], resdir=None):
    #for each date directory
    if not dirnames:
        print(MODULE_IDENTIFIER + "Warning: Targets not specified. Looking under current directory")
        dirnames = os.listdir('./*.mda')
        if not dirnames:
            raise Exception("Could not find MDA files in current directory. Try specifying MDA location")

    # TODO: Currently, code relies on the provision of absolute paths. Relative paths will not work.
    if resdir is None:
        resdir = os.getcwd() + '/softlinks'

    for ep_idx, epdirmda in enumerate(dirnames):
        print(MODULE_IDENTIFIER + "Epoch %d. MDA File: %s"%(ep_idx, epdirmda))
        try:
            print(MODULE_IDENTIFIER + "Found EPOCH " + epdirmda)
            for eptetmda in os.listdir(epdirmda+'/'):
                if '.nt' in eptetmda:
                    # Get the tetrode index
                    ntr = eptetmda.split('.')[1]
                    print(MODULE_IDENTIFIER + "Tetrode %d in file %s."%(int(ntr.strip(TETRODE_EXTENSION)), eptetmda))
                    srclink = epdirmda+'/'+eptetmda
                    ntdir = resdir + '/' + ntr
                    destlink = ntdir + '/' + eptetmda
                    print("Creating softlink...")
                    print("Source: " + srclink)
                    print("Destination: " + destlink)
                    make_sure_path_exists(srclink)
                    make_sure_path_exists(ntdir)
                    removeNTfile(destlink) #to overwrite. remove ntlink if it already exists
                    #create directory of sym links to original mda
                    os.symlink(srclink, destlink)
                else:
                    print("Warning: Found file %s, which is not a tetrode!"%eptetmda)
        except Exception as err:
            print("Unable to complete softlink creation for epoch %s"%epdirmda)
            print(err)
        finally:
            # TODO: Delete any softlinks that might have been made already at this point.
            pass

def make_sure_path_exists(path):
    import os, errno
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def removeNTfile(ntrode_filename):
    import os, errno
    try:
        os.remove(ntrode_filename)
    except OSError as e:  # this would be "except OSError, e:" before Python 2.6
        if e.errno != errno.ENOENT:  # errno.ENOENT = no such file or directory
            raise  # re-raise exception if a different error occurred

if __name__ == "__main__":
    # User can supply a list of mda files which all need to be combined for spike sorting.
    dirnames = []
    resname = None
    try:
        resname = sys.argv[1]
        if len(sys.argv) > 2:
            for dir_idx, dirname in enumerate(sys.argv[2:]):
                dirnames.append(dirname)
        make_mda_ntrodeEpoch_links(dirnames, resname)
    except Exception as err:
        print(MODULE_IDENTIFIER + "Expecting source/destination directories")
        print(MODULE_IDENTIFIER + "Usage python mda_utils.py <target> <sources>")
        print(err)
