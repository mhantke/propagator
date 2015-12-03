#!/usr/bin/env python
import argparse
import os
import condor
import condor.utils
from condor.utils.log import log_info
import logging
logger = logging.getLogger("condor")

#if __name__ == "__main__":
def main():
    parser = argparse.ArgumentParser(description='Condor - simulation of single particle X-ray diffraction patterns')
    parser.add_argument('-v', '--verbose', dest='verbose',  action='store_true', help='verbose mode', default=False)
    parser.add_argument('-d', '--debug', dest='debug',  action='store_true', help='debugging mode (even more output than in verbose mode)', default=False)
    parser.add_argument('-n', '--number-of-patterns', metavar='number_of_patterns', type=int,
                        help="number of patterns to be simulated", default=1)
    args = parser.parse_args()
    if not os.path.exists("./condor.conf"):
        parser.error("Cannot find configuration file \"condor.conf\" in current directory.")
    if args.verbose:
        logger.setLevel("INFO")
    if args.debug:
        logger.setLevel("DEBUG")

    E = condor.experiment.experiment_from_configfile("./condor.conf")
        
    # FOR BENCHMARKING
    #from pycallgraph import PyCallGraph
    #from pycallgraph.output import GraphvizOutput
    #from pycallgraph import Config
    #from pycallgraph import GlobbingFilter
    #config = Config()
    #config.trace_filter = GlobbingFilter(exclude=[
    #'pycallgraph.*',
    #'numpy.*',
    #])
    #with PyCallGraph(output=GraphvizOutput(),config=config):

    W = condor.utils.cxiwriter.CXIWriter("./condor.cxi")
    for i in range(args.number_of_patterns):
        res = E.propagate()
        W.write(res)
    W.close()

    