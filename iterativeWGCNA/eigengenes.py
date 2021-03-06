# pylint: disable=invalid-name
# pylint: disable=unused-import
'''
manage eigengenes
'''

import logging

import rpy2.robjects as ro
from .r.imports import base, stats, rsnippets
from .io.utils import write_data_frame

class Eigengenes(object):
    '''
    manage and manipulate eigengene matrices
    '''

    def __init__(self, matrix=None):
        self.logger = logging.getLogger('iterativeWGCNA.Modules')
        self.matrix = matrix


    def extract_from_blocks(self, iteration, blocks, samples):
        '''
        extract eigenenges from blockwise WGCNA results
        '''
        self.matrix = rsnippets.extractEigengenes(iteration, blocks, samples)


    def samples(self):
        '''
        return sample names
        '''
        return self.matrix.names


    def nrows(self):
        '''
        wrapper for returning number of rows in
        the eigengene matrix
        '''

        return self.matrix.nrow


    def load_matrix_from_file(self, fileName):
        '''
        loads eigengenes from file into an R DataFrame
        '''
        self.matrix = ro.DataFrame.from_csvfile(fileName, sep='\t',
                                                header=True, row_names=1)


    def write(self, isFinal=False):
        '''
        writes the eigengene matrix to file
        '''
        fileName = 'eigengenes-final.txt' if isFinal else 'eigengenes.txt'
        write_data_frame(self.matrix, fileName, 'Module')


    def similarity(self, module):
        '''
        calculate similarity between eigengene for a specific
        module and all the other eigengenes
        '''
        sim = base().as_data_frame(stats().cor(base().t(self.matrix), \
                                               base().t(self.matrix.rx(module, True))))
        return sim


    def correlation(self, m1, m2):
        '''
        calculate correlation between two module eigengenes
        '''
        e1 = self.get_module_eigengene(m1)
        e2 = self.get_module_eigengene(m2)
        cor = base().as_data_frame(stats().cor(base().t(e1), base().t(e2)))
        cor = round(cor.rx(1, 1)[0], 1)
        return cor


    def equal(self, m1, m2, threshold=0.0):
        '''
        check if 2 module eigengenes are "equivalent"
        (1 - correlation <= threshold)
        '''
        cor = self.correlation(m1, m2)
        return 1.0 - cor <= threshold


    def get_module_eigengene(self, module):
        '''
        return a module eigengene
        '''
        return self.matrix.rx(module, True)


    def extract_subset(self, modules):
        '''
        return a submatrix
        '''
        return self.matrix.rx(ro.StrVector(modules), True)


    def is_empty(self):
        '''
        return True if matrix is empty
        '''
        return self.matrix.nrow == 0


    def update_to_subset(self, modules):
        '''
        update matrix to subset specified by modules
        '''
        self.matrix = self.extract_subset(modules)
