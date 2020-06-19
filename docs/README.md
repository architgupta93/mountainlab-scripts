## Instructions for setting up MountainSort (with trodes)
1. Use conda for setting up a virtual environment

            $ conda create -n mountainlab
            $ conda activate mountainlab

2. Install mountain lab, its processors and visualization tools

            $ conda install -c flatiron -c conda-forge mountainlab mountainlab_pytools
            $ conda install -c flatiron -c conda-forge ml_ephys
            $ conda install -c flatiron -c conda-forge qt-mountainview ephys-viz

3. Install helper functions and other algorithms

            $ conda install -c flatiron -c conda-forge ml_ms3
            $ conda install -c flatiron -c conda-forge ml_pyms
            $ conda install -c flatiron -c conda-forge ml_ms4alg

The github page says that qt-mountainview is a temporary solution while they develop ephys-viz (In case stuff stops working in the future).

4. Test that the installation works by running their hello world process

            $ ml-run-process hello.world

5. Time to do some spike sorting.
    a. Generate MDA from the spike-gadgets .rec file

    $ exportmda -rec <rec_file> -outputdirectory <output_dir>

6. To sort segments, you need to add a few packages too.
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

## Using the supplied sorting interface.
1. I recommend using the help functions to understand how the supplied scripts work. For example, if you run the following command, it should produce a set of commandline arguments that you can provide to run commandline sorting.

    $ python MS4batch.py --help

2. This should produce the following output:

```
usage: MS4batch.py [-h] [--animal <animal-name>]
                   [--mask-artifacts <mask-artifacts>]
                   [--clear-files <clear-files>]
                   [--tetrode-begin <tetrode-begin>]
                   [--tetrode-end <tetrode-end>] [--date YYYYMMDD]
                   [--data-dir <[MDA] data-directory>]
                   [--output-dir <output-directory>]

MountainSort Batch Helper.

optional arguments:
  -h, --help            show this help message and exit
  --animal <animal-name>
                        Animal name
  --mask-artifacts <mask-artifacts>
                        Mark signal artifacts
  --clear-files <clear-files>
                        Clear additional files
  --tetrode-begin <tetrode-begin>
                        First tetrode to sort
  --tetrode-end <tetrode-end>
                        Last tetrode to sort
  --date YYYYMMDD       Experiment date
  --data-dir <[MDA] data-directory>
                        Data directory from which MDA files should be read.
  --output-dir <output-directory>
                        Output directory where sorted spike data should be
                        stored
```

3. If the step above produces python errors, it is very likely that you are missing some of the required libraries. Some of the commonly missing libraries include:

    
