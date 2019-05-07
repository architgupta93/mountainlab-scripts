"""
Commandline argument parsing and other helper functions
"""

import argparse

def parse_commandline_arguments():
    """
    Parse commandline arguments for the program
    :arguments: Complete argument string passed in (Typically, just pass in sys.argv)
    :returns: Commandline arguments, parsed and returned as a tuple
    """

    # Setting up the parser
    parser = argparse.ArgumentParser(description='MountainSort Batch Helper.')
    parser.add_argument('--animal', metavar='<animal-name>', help='Animal name')
    parser.add_argument('--mask-artifacts', metavar='<mask-artifacts>', help='Mark signal artifacts', type=bool)
    parser.add_argument('--clear-files', metavar='<clear-files>', help='Clear additional files', type=bool)
    parser.add_argument('--tetrode-begin', metavar='<tetrode-begin>', help='First tetrode to sort', type=int)
    parser.add_argument('--tetrode-end', metavar='<tetrode-end>', help='Last tetrode to sort', type=int)
    parser.add_argument('--date', metavar='YYYYMMDD', help='Experiment date', type=int)
    parser.add_argument('--data-dir', metavar='<[MDA] data-directory>', help='Data directory from which MDA files should be read.')
    parser.add_argument('--output-dir', metavar='<output-directory>', help='Output directory where sorted spike data should be stored')
    args = parser.parse_args()
    # print(args)
    return args
