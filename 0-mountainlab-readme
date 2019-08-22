Instructions for setting up MountainLab (with trodes)
1. Use conda for setting up a virtual environment

            $ conda create -n mountainlab
            $ conda activate mountainlab

2. Install mountain lab, its processors and visualization tools
            $ conda install -c flatiron -c conda-forge mountainlab mountainlab_pytools
            $ conda install -c flatiron -c conda-forge ml_ephys
            $ conda install -c flatiron -c conda-forge qt-mountainview ephys-viz

2b. Install helper functions and other algorithms
            $ conda install -c flatiron -c conda-forge ml_ms3
            $ conda install -c flatiron -c conda-forge ml_pyms
            $ conda install -c flatiron -c conda-forge ml_ms4alg
The github page says that qt-mountainview is a temporary solution while they develop ephys-viz (In case stuff stops working in the future).

3. Test that the installation works by running their hello world process
            $ ml-run-process hello.world

4. Time to do some spike sorting.
    a. Generate MDA from the spike-gadgets .rec file
    exportmda -rec <rec_file> -outputdirectory <output_dir>

5. To sort segments, you need to add a few packages too.
    a. franklab_mstaggedcuration
    b. franklab_msdrift

    Find them on franklab's bitbucket page. We should probably make a copy for
    ourselves too (one that works.)
            $ ml-config

    This should produce the package directory for conda. Go to that directory
    and add these pacakges there. Try running the code MS4batch.py. 

                ==== If running the code does not work as is ====
    For both these packages, we need to change the system-path for it to work!
    Also the mountainlab package has changed to ml_pyms from pyms
