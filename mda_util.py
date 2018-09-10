#! /home/droumis/anaconda3/bin/python3
#run this from the preprocessing directory containing all dates' data

def make_mda_ntrodeEpoch_links(filename=None):
    import os
    #for each date directory
    if filename is None:
        filename = './'
    print(os.listdir(filename))

    for datedir in os.listdir(filename):
        date = datedir.split('_')[0]
        print(date)
        #for each ep.mda directory
        for epdirmda in os.listdir('./'+date):
            if '.mda' in epdirmda:
                print(epdirmda)
                # for each nt.mda file
                for eptetmda in os.listdir('./'+date+'/'+epdirmda):
                    if '.nt' in eptetmda:
                        print(eptetmda)
                        an = eptetmda.split('_')[1]
                        endf = eptetmda.split('_')[-1]
                        ntr = endf.split('.')[1]
                        cwd = os.getcwd()
                        srclink = cwd+'/'+datedir+'/'+epdirmda+'/'+eptetmda
                        mntdir = date + '_' + an + '.mnt'
                        ntdir = date+'_'+an+ '.'+ntr+'.mnt'
                        destlink = cwd+'/'+datedir+'/'+mntdir+'/'+ntdir+'/'+eptetmda
                        print()
                        print(srclink)
                        print(destlink)
                        # print(srclink)
                        # print(destlink)
                        make_sure_path_exists(cwd+'/'+datedir+'/'+mntdir)
                        make_sure_path_exists(cwd+'/'+datedir+'/'+mntdir+'/'+ntdir)
                        removeNTfile(destlink) #to overwrite. remove ntlink if it already exists
                        #create directory of sym links to original mda
                        os.symlink(srclink, destlink)
#        return

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

#def createSymlink():
if __name__ == "__main__":
    make_mda_ntrodeEpoch_links()
