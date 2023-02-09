#!/bin/python

import pandas as pd
import sys
import logging

# Author: Grigori Fedorets


def PPReadPhysicalParameters(clr_datafile, beginLoc, chunkSize, filesep):
    """
    PPReadPhysicalParameters.py


    Description: This task reads in the physical parameters file and puts it into a
    single pandas dataframe for further use downstream by other tasks.

    The format of the colours is:

    id   colour1 colour2 etc


    Mandatory input:      string, clr_datafile, name of colour data file
                          integer, beginLoc, location in file where reading begins
                          integer, chunkSize, length of chunk to be read in
                          string, filesep, separator used in input file, blank or comma

    Output:               pandas dataframe



    usage: padafr=PPReadColours(clr_datafile, beginLoc, chunkSize,filesep)
    """

    pplogger = logging.getLogger(__name__)

    if (filesep == "whitespace"):
        padafr = pd.read_csv(clr_datafile, delim_whitespace=True, skiprows=range(1, beginLoc + 1), nrows=chunkSize, header=0)
    elif (filesep == "comma" or filesep == "csv"):
        padafr = pd.read_csv(clr_datafile, skiprows=range(1, beginLoc + 1), nrows=chunkSize, header=0)

    # check for nans or nulls

    if padafr.isnull().values.any():
        pdt = padafr[padafr.isna().any(axis=1)]
        print(pdt)
        inds = str(pdt['ObjID'].values)
        outstr = "ERROR: uninitialised values when reading colour file. ObjID: " + str(inds)
        pplogger.error(outstr)
        sys.exit(outstr)

    try:
        padafr['ObjID'] = padafr['ObjID'].astype(str)
    except KeyError:
        pplogger.error('ERROR: PPReadPhysicalParameters: Cannot find ObjID in column headings. Check input and input format.')
        sys.exit('ERROR: PPReadPhysicalParameters: Cannot find ObjID in column headings. Check input and input format.')

    return padafr
