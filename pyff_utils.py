from collections import defaultdict
import scipy.io

def py_evaluatefilter(base_dir, anim, datatype, days, filtstrings):
    
    # this currently only looks for information in the first ep of every day - ok for tetinfo but should be made more flexible
    # also should make this work for filtering taskinfo and cellinfo

    fname = base_dir+anim+'/filterframework/'+anim+datatype+'.mat'
    tetfile = scipy.io.loadmat(fname,squeeze_me=True,struct_as_record=False)
    tetlist = defaultdict(list)
    for day in days:
        for index, t in enumerate(tetfile[datatype][day][0][:],1):
            if hasattr(t,filtstrings[0]):
                if filtstrings[1] in getattr(t,filtstrings[0]): 
                    tetlist[day].append(index)
    return tetlist