#!/usr/bin/python3
#run this from the preprocessing directory containing all dates' data
import os
import sys

MODULE_IDENTIFIER = "[MDA Linker] "
MDA_EXTENSION = '.mda'
TETRODE_EXTENSION = '.nt'

def make_mda_ntrodeEpoch_links(dirnames=[], resdir=None):
    #for each date directory
    if len(dirnames) == 0:
        print(MODULE_IDENTIFIER + "Warning: Targets not specified. Looking under current directory")
        dirnames = os.listdir('./')
        if len(dirnames) == 0:
            raise Exception("Could not find MDA files in current directory. Try specifying MDA location")

    # TODO: Currently, code relies on the provision of absolute paths. Relative paths will not work.
    if resdir is None:
        resdir = os.getcwd() + '/softlinks'
    for ep_idx, epdirmda in enumerate(dirnames):
        try:
            print(MODULE_IDENTIFIER + "Found EPOCH " + epdirmda)
            for eptetmda in os.listdir(epdirmda+'/'):
                if '.nt' in eptetmda:
                    # Get the tetrode index
                    ntr = eptetmda.split('.')[1]
                    print(MODULE_IDENTIFIER + "Tetrode %d in file %s."%(int(ntr.strip(TETRODE_EXTENSION)), eptetmda))
                    srclink = epdirmda+'/'+eptetmda
                    mntdir = resdir + '.mnt'
                    ntdir = resdir + '/' + ntr + '.mnt'
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
            return

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
