'''
I/O Utils
'''
from __future__ import print_function
from __future__ import with_statement

from sys import stderr
import os
import rpy2.robjects as ro
from ..r.imports import r_utils

def warning(*objs):
    '''
    wrapper for writing to stderr
    '''
    print(*objs, file=stderr)
    stderr.flush()


def create_dir(dirName):
    '''
    check if directory exists in the path, if not create
    '''
    try:
        os.stat(dirName)
    except OSError:
        os.mkdir(dirName)

    return dirName


def write_data_frame(df, fileName, rowLabel):
    '''
    write data frame to file; creates new file
    if none exists, otherwise appends new eigengenes
    to existing file
    '''
    try:
        os.stat(fileName)
    except OSError:
        header = (rowLabel,) + tuple(df.colnames)
        with open(fileName, 'w') as f:
            print('\t'.join(header), file=f)
    finally:
        df.to_csvfile(fileName, quote=False, sep='\t', col_names=False, append=True)

def read_data(fileName):
    '''
    read gene expression data into a data frame
    and convert numeric (integer) data to real
    '''
    data = ro.DataFrame.from_csvfile(fileName, sep='\t', header=True, row_names=1)
    return r_utils.numeric2real(data)


def transpose_file_contents(fileName):
    '''
    read in a file to a dataframe, transpose, and output
    use this instead of R transforms b/c R will concatenate
    an "X" to gene ids starting with a number
    '''
    with open(fileName, 'r') as f:
        content = [line.rstrip().split() for line in f]

    with open(fileName, 'w') as f:
        for line in zip(*content):
            print('\t'.join(line), file=f)