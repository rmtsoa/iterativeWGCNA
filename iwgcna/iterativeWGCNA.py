#!/usr/bin/env python2.7
"""
Perform iterative WGCNA analysis

python dependencies:
  * rpy2

R dependencies:
  * igraph
  * WGCNA
  * lattice
"""

import logging
import sys
from time import strftime
from . import warning
from .r.utils import initialize_r_workspace
from . import membership, kme, eigengenes, expression
from .utils import io as iwgcna_io
from .utils import log
from .import process as manager

def iterative_wgcna(data, args):
    '''
    iteratively apply WGCNA until convergence
    conditions are met
    '''
    runId = 1
    passId = 1

    kmeMap = kme.initialize(data)
    membershipMap = membership.initialize(data)
    passData = data # input data for pass
    iterationData = passData # input data for iteration

    algConverged = False
    passConverged = False

    while not algConverged:
        iteration = manager.set_iteration_label(runId, passId)

        if args.verbose:
            warning("Running iteration: " + iteration)

        # run an iteration of WGCNA + goodness of fit test
        membershipMap, kmeMap = manager.run_iteration(
            iteration, iterationData, membershipMap, kmeMap,
            args.wgcnaParameters, args.saveBlocks)

        moduleCount = membership.count_modules(membershipMap, iterationData.rownames)
        classifiedGeneCount = membership.count_classified_genes(membershipMap, iterationData.rownames)

        # if there are no residuals
        # (classified gene count = number of genes input)
        # then the pass has converged
        if classifiedGeneCount == iterationData.nrow:
            passConverged = True

        # if no modules were detected,
        # then the algorithm has converged
        if moduleCount == 0:
            algConverged = True
            message = "No modules detected for iteration " + iteration \
                      + ". Classification complete."
            logging.info(message)
            if args.verbose:
                warning(message)

        manager.write_gene_counts(iteration, iterationData.nrow, classifiedGeneCount)

        if passConverged:
            summary = log.pass_completion(passId, iteration, passData.nrow,
                                          classifiedGeneCount, moduleCount)
            if args.verbose:
                warning(summary)

            # set residuals of the pass as new
            # input dataset for the next pass
            passData = expression.get_residuals(passData, membershipMap)

            # and as the dataset for the current iteration
            iterationData = passData

            # increment pass id and reset run id
            passId = passId + 1
            runId = 1

            # reset pass convergence flag
            passConverged = False

        else:
            # otherwise remove residuals and run again
            # with classified gene set to evaluate whether
            # classification can be improved after
            # connections to pruned genes are removed
            iterationData = expression.remove_residuals(iterationData, membershipMap)
            runId = runId + 1

    return membershipMap, kmeMap


def main(args):
    '''
    main function:
    1. run iterative WGCNA
    2. make last check goodness of fit test to
       reassign module membership(s) after all
       iterations
    3. transpose output files so samples are in
       columns and genes in rows to improve
       readability and so that files are EXCEL friendly
    '''
    logger = None
    try:
        logger, data = initialize(args)

        # run iterative WGCNA
        membershipMap, kmeMap = iterative_wgcna(data, args)
        
        # use kME goodness of fit to reassign module
        # membership now that all modules are estimated
        if args.verbose:
            warning("Making final goodness of fit assessment")
            modules = membership.get_modules(membershipMap)
            logger.info("Found " + str(len(modules)) + " modules.")
            logger.info(modules)

        # extract final eigengene matrix
        eigengeneMatrix = eigengenes.load_from_file('eigengenes.txt')
        eigengeneMatrix = eigengenes.extract_modules(eigengeneMatrix, modules)
        eigengenes.write(eigengeneMatrix, True)

        reassignedCount, membershipMap, kmeMap = membership.best_fit(membershipMap, eigengeneMatrix, data,
                                                                     kmeMap, args.wgcnaParameters)
        logging.info("Reassigned " + str(reassignedCount) + " genes in final kME review.")
        if args.verbose:
            warning("Reassigned " + str(reassignedCount) + " genes in final kME review.")

        membership.write('final', membershipMap, True)
        kme.write('final', kmeMap)

        if args.verbose:
            warning("Generating final output")

        # transpose membership and kME files (so samples are columns)
        iwgcna_io.transpose_file_contents("pre-pruning-membership.txt", 'Gene')
        iwgcna_io.transpose_file_contents("membership.txt", 'Gene')
        iwgcna_io.transpose_file_contents("eigengene-connectivity.txt")

        logger.info('iWGCNA: SUCCESS')

    except Exception:
        if logger is not None:
            logger.exception('iWGCNA: FAILED')
        else:
            raise

    finally:
        if logger is not None:
            logger.info(strftime("%c"))


def initialize(args):
    if args.verbose:
        warning("Initializing workspace")

    # initialize R workspace and logs
    iwgcna_io.create_dir(args.workingDir)
    initialize_r_workspace(args.workingDir, args.allowWGCNAThreads)

    logger = log.initialize(args.workingDir)
    log.parameters(args)

    # load input data
    if args.verbose:
        warning("Loading Data")

    # gives a weird R error that I'm having trouble catching
    # TODO: identify the exact exception 
    try:
        data = iwgcna_io.read_data(args.inputFile)
    except:
        logger.error("Unable to open input file: " + args.inputFile)
        sys.exit(1)

    log.input_data(args.inputFile, data.ncol, data.nrow)

    return logger, data

__author__ = 'Emily Greenfest-Allen'
__copyright__ = 'Copyright 2016, University of Pennsylvania'

