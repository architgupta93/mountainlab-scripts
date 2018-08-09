# franklab_MS4
## This repo contains a python notebook (MS4batch) for managing mountainsort processing across animals, days, and ntrodes. 
MS4 batch relies on pyplines: collections of processors that perform a collective function, such as preprocessing. 
pyplines contains calls to the helper module proc2py, which serves as an interface to make processors written in any language callable in python. 
Ideally, each user will have a flexible notebook or notebooks to use for managing their sorts, but will use a standardized set of pyplines that might be common to the whole lab. 

## This system has been built using the MS4 (mountainlab-js) conda package. 
It also makes use of the following accessory processors:

msdrift: https://bitbucket.org/franklab/franklab_msdrift/src/master/ 

ms_tagged_curation: https://bitbucket.org/franklab/franklab_mstaggedcuration/src/master/ 


