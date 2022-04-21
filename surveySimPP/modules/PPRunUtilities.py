#!/usr/bin/python
# Utility functions used in the running of surveySimPP.py.

import logging
import os, sys
import numpy as np
import pandas as pd
import configparser
from datetime import datetime
from . import PPOutWriteCSV, PPOutWriteSqlite3, PPOutWriteHDF5
from . import PPReadOrbitFile, PPCheckOrbitAndPhysicalParametersMatching, PPReadCometaryInput
from . import PPReadIntermDatabase, PPReadEphemerides, PPJoinPhysicalParametersPointing
from . import PPJoinOrbitalData, PPMatchPointingToObservations, PPReadPhysicalParameters

def PPGetLogger(    
        LOG_FORMAT     = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s ',
        LOG_NAME       = '',
        LOG_FILE_INFO  = 'postprocessing.log',
        LOG_FILE_ERROR = 'postprocessing.err'):


    #LOG_FORMAT     = '',
    log           = logging.getLogger(LOG_NAME)
    log_formatter = logging.Formatter(LOG_FORMAT)

    # comment this to suppress console output
    #stream_handler = logging.StreamHandler()
    #stream_handler.setFormatter(log_formatter)
    #log.addHandler(stream_handler)
    
    DSTR=datetime.now().strftime('%Y%m%d%H%M')
    CPID=os.getpid()
    
    LOG_FILE_INFO=str(DSTR + '-' + str(CPID) + '-' + LOG_FILE_INFO)
    LOG_FILE_ERROR=str(DSTR + '-' + str(CPID) + '-' + LOG_FILE_ERROR)
    

    file_handler_info = logging.FileHandler(LOG_FILE_INFO, mode='w')
    file_handler_info.setFormatter(log_formatter)
    file_handler_info.setLevel(logging.INFO)
    log.addHandler(file_handler_info)

    file_handler_error = logging.FileHandler(LOG_FILE_ERROR, mode='w')
    file_handler_error.setFormatter(log_formatter)
    file_handler_error.setLevel(logging.ERROR)
    log.addHandler(file_handler_error)

    log.setLevel(logging.INFO)

    return log


def PPGetOrExit(config, section, key, message):
    # from Shantanu Naidu, objectInField
    try:
        return config[section][key]
    except KeyError:
        logging.error(message)
        sys.exit(message)
        

def PPGetOrPass(config, section, key, message):
    # as PPGetOrExit, except if the config variable doesn't exist, returns 0
    # essentially turns off filters if the variable isn't given
    try:
        return config[section][key]
    except KeyError:
        logging.info(message)
        return 0
                    
        
def PPToBool(value):
    valid = {'true': True, 't': True, '1': True, 'True': True,
             'false': False, 'f': False, '0': False, 'False': False
             }   

    if isinstance(value, bool):
        return value

    if not isinstance(value, str):
        raise ValueError('invalid literal for boolean. Not a string.')

    lower_value = value.lower()
    if lower_value in valid:
        return valid[lower_value]
    else:
        raise ValueError('invalid literal for boolean: "%s"' % value)


def PPConfigFileParser(configfile, survey_name):
    """
    Author: Steph Merritt

    Description: Parses the config file, error-handles, then assigns the values into a single 
    dictionary, which is passed out. Mostly copied out of old version of run script.

    Chose not to use the original ConfigParser object for readability: it's a dict of 
    dicts, so calling the various values can become quite unwieldy.

    This could easily be broken up even more, and probably should be.	

    Mandatory input:	string, configfile, string filepath of the config file
                        string, survey_name, command-line argument containing survey name

    Output: 			dictionary of variables taken from the config file

    """
	
    config = configparser.ConfigParser()
    config.read(configfile)

    pplogger = logging.getLogger(__name__)

    config_dict = {}
    config_dict['pointingFormat'] = PPGetOrExit(config, 'INPUTFILES', 'pointingFormat', 'ERROR: no pointing simulation format is specified.')
    config_dict['filesep'] = PPGetOrExit(config, 'INPUTFILES', 'auxFormat', 'ERROR: no auxilliary data format specified.')  

    config_dict['objecttype'] = PPGetOrExit(config, 'OBJECTS', 'objecttype', 'ERROR: no object type provided.')    
    if config_dict['objecttype'] not in ['asteroid', 'comet']:
        pplogger.error('ERROR: objecttype is neither an asteroid or a comet.') 
        sys.exit('ERROR: objecttype is neither an asteroid or a comet.')

    config_dict['ephemerides_type'] = PPGetOrExit(config, 'INPUTFILES', 'ephemerides_type', 'ERROR: no ephemerides type provided.')
    config_dict['pointingdatabase'] = PPGetOrExit(config, 'INPUTFILES', 'pointingdatabase', 'ERROR: no pointing database provided.')
    PPFindFileOrExit(config_dict['pointingdatabase'], 'pointingdatabase')
    config_dict['ppdbquery'] = PPGetOrExit(config, 'INPUTFILES', 'ppsqldbquery', 'ERROR: no pointing database SQLite3 query provided.')

    config_dict['othercolours'] = [e.strip() for e in config.get('FILTERS', 'othercolours').split(',')]
    config_dict['observing_filters'] = [e.strip() for e in config.get('FILTERS', 'observing_filters').split(',')]    
    if (len(config_dict['othercolours']) != len(config_dict['observing_filters'])-1):
        pplogger.error('ERROR: mismatch in input config colours and filters: len(othercolours) != len(observing_filters) - 1')
        sys.exit('ERROR: mismatch in input config colours and filters: len(othercolours) != len(observing_filters) - 1')
	
    PPCheckFiltersForSurvey(survey_name, config_dict['observing_filters'])
	 
    config_dict['phasefunction'] = PPGetOrExit(config,'PHASE', 'phasefunction', 'ERROR: phase function not defined.')
    config_dict['trailingLossesOn'] = PPToBool(config['PERFORMANCE']['trailingLossesOn'])

    config_dict['cameraModel'] = PPGetOrExit(config, 'PERFORMANCE', 'cameraModel', 'ERROR: camera model not defined.')	
	
    if config_dict['cameraModel'] not in ['circle', 'footprint']:
        pplogger.error('ERROR: cameraModel should be either circle or footprint.')
        sys.exit('ERROR: cameraModel should be either circle or footprint.')        
	
    elif (config_dict['cameraModel'] == 'footprint'):
        config_dict['footprintPath'] = PPGetOrExit(config, 'INPUTFILES', 'footprintPath', 'ERROR: no camera footprint provided.')
        PPFindFileOrExit(config_dict['footprintPath'], 'footprintPath')
		
        try:
            check_for_fillfactor = config['FILTERINGPARAMETERS']['fillfactor']
            pplogger.error('ERROR: fill factor supplied in config file but camera model is not "circle".')
            sys.exit('ERROR: fill factor supplied in config file but camera model is not "circle".')
        except KeyError:
            config_dict['fillfactor'] = 1.0
		
    elif (config_dict['cameraModel']) == 'circle':
        config_dict['fillfactor'] = float(PPGetOrExit(config, 'FILTERINGPARAMETERS', 'fillfactor', 'ERROR: no fill factor specified for circular footprint.'))

    config_dict['brightLimit'] = float(PPGetOrPass(config, 'FILTERINGPARAMETERS', 'brightLimit', 'Brightness limit not supplied. No brightness filter will be applied.'))
    config_dict['SNRLimit'] = float(PPGetOrPass(config, 'FILTERINGPARAMETERS', 'SNRLimit', 'SNR limit not supplied. SNR limit defaulting to 2 sigma.'))	
    config_dict['magLimit'] = float(PPGetOrPass(config, 'FILTERINGPARAMETERS', 'magLimit', 'Magnitude limit not supplied. No magnitude cut will be applied.'))
    
    if not config_dict['SNRLimit']: config_dict['SNRLimit'] = 2.0	
    
    if config_dict['brightLimit'] and (isinstance(config_dict['brightLimit'],(float,int))==False):
        pplogger.error('ERROR: brightness limit is not an int or float.')
        sys.exit('ERROR: brightness limit is not an int or float.')
    
    if (isinstance(config_dict['SNRLimit'],(float,int))==False or config_dict['SNRLimit'] < 0):
        pplogger.error('ERROR: SNR limit is negative, or not an int or float.')
        sys.exit('ERROR: SNR limit is negative, or not an int or float.')
    
    if config_dict['magLimit'] and (isinstance(config_dict['magLimit'],(float,int))==False or config_dict['magLimit'] < 0):
        pplogger.error('ERROR: magnitude limit is negative, or not an int or float.')
        sys.exit('ERROR: magnitude limit is negative, or not an int or float.')
    
    config_dict['inSepThreshold'] = float(PPGetOrPass(config, 'FILTERINGPARAMETERS', 'inSepThreshold', 'Separation threshold not supplied for SSP filtering.'))
    config_dict['minTracklet'] = int(PPGetOrPass(config, 'FILTERINGPARAMETERS', 'minTracklet', 'Minimum tracklet length not supplied for SSP filtering.'))
    config_dict['noTracklets'] = int(PPGetOrPass(config, 'FILTERINGPARAMETERS', 'noTracklets', 'Number of tracklets not supplied for SSP filtering.'))
    config_dict['trackletInterval'] = float(PPGetOrPass(config,'FILTERINGPARAMETERS','trackletInterval', 'Tracklet interval not supplied for SSP filtering.'))
    config_dict['SSPDetectionEfficiency'] = float(PPGetOrPass(config, 'FILTERINGPARAMETERS', 'SSPDetectionEfficiency', 'Detection efficiency not supplied for SSP filtering.'))
	
    if config_dict['inSepThreshold'] and config_dict['minTracklet'] and config_dict['noTracklets'] and config_dict['trackletInterval'] and config_dict['SSPDetectionEfficiency']:
        
        # only error handles these values if they are supplied
        if (config_dict['minTracklet'] < 1 or isinstance(config_dict['minTracklet'],int)==False):
            pplogger.error('ERROR: minimum length of tracklet is zero or negative, or not an integer.')
            sys.exit('ERROR: minimum length of tracklet is zero or negative, or not an integer.')
        
        if (config_dict['noTracklets']  < 1 or isinstance(config_dict['noTracklets'], int)== False):
            pplogger.error('ERROR: number of tracklets is zero or less, or not an integer.')
            sys.exit('ERROR: number of tracklets is zero or less, or not an integer.')    
        
        if (config_dict['trackletInterval'] <= 0.0 or isinstance(config_dict['trackletInterval'],(float,int))==False):
            pplogger.error('ERROR: tracklet appearance interval is negative, or not a number.')
            sys.exit('ERROR: tracklet appearance interval is negative, or not a number.')
        
        if (config_dict['SSPDetectionEfficiency'] > 1.0 or config_dict['SSPDetectionEfficiency'] > 1.0 or isinstance(config_dict['SSPDetectionEfficiency'],(float,int))==False):
            pplogger.error('ERROR: SSP detection efficiency out of bounds (should be between 0 and 1.), or not a number.')
            sys.exit('ERROR: SSP detection efficiency out of bounds (should be between 0 and 1.), or not a number.')
              
        config_dict['SSPFiltering'] = True  
    
    elif not config_dict['inSepThreshold'] and not config_dict['minTracklet'] and not config_dict['noTracklets'] and not config_dict['trackletInterval'] and not config_dict['SSPDetectionEfficiency']:
        config_dict['SSPFiltering'] = False
    else:
        pplogger.error('ERROR: only some SSP filtering variables supplied. Supply all five required variables for SSP filter, or none to turn filter off.')
        sys.exit('ERROR: only some SSP filtering variables supplied. Supply all five required variables for SSP filter, or none to turn filter off.')
			
    config_dict['outpath'] = PPGetOrExit(config, 'OUTPUTFORMAT', 'outpath', 'ERROR: out path not specified.')   
    config_dict['outfilestem'] = PPGetOrExit(config, 'OUTPUTFORMAT', 'outfilestem', 'ERROR: name of output file stem not specified.')
	
    PPFindFileOrExit(config_dict['outpath'], 'outpath')

    config_dict['outputformat'] = PPGetOrExit(config, 'OUTPUTFORMAT', 'outputformat', 'ERROR: output format not specified.')   
    if config_dict['outputformat'] not in ['csv', 'separatelyCSV', 'separatelyCsv', 'separatelycsv', 'sqlite3', 'hdf5', 'HDF5', 'h5']:
        pplogger.error('ERROR: output format should be either csv, separatelyCSV, sqlite3 or hdf5.')
        sys.exit('ERROR: output format should be either csv, separatelyCSV, sqlite3 or hdf5.')

    config_dict['sizeSerialChunk'] = int(config['GENERAL']['sizeSerialChunk'])

    return config_dict

def PPCheckFiltersForSurvey(survey_name, observing_filters):
    """
    Author: Steph Merritt
    
    When given a list of filters, this function checks to make sure they exist in the
    user-selected survey. Currently only has options for LSST, but can be expanded upon
    later. If the filters given in the config file do not match the survey filters,
    the function exits the program with an error.
    
    Parameters:
    -----------
    survey_name: string containing survey name
    observing_filters: list of strings with colour filters.
    
    """
    
    pplogger = logging.getLogger(__name__)

    if survey_name in ["LSST", "lsst"]:

        lsst_filters = ['u', 'g', 'r', 'i', 'z', 'y']
        filters_ok = all(elem in lsst_filters for elem in observing_filters)

        if not filters_ok:
            bad_list = np.setdiff1d(observing_filters,lsst_filters)
            pplogger.error('ERROR: Filter(s) {} given in config file are not recognised filters for {} survey.'.format(bad_list, survey_name))
            pplogger.error('Accepted {} filters: {}'.format("LSST", lsst_filters))
            pplogger.error('Change observing_filters in config file or select another survey.')
            sys.exit('ERROR: Filter(s) {} given in config file are not recognised filters for {} survey.'.format(bad_list, survey_name))

            
def PPPrintConfigsToLog(configs):
    """
    Author: Steph Merritt

    Description: Prints all the values from the config file to the log. Copied out of the runscript.

    Mandatory input:	dict, configs, dictionary of config variables created by PPConfigFileParser
                    
    Output: none

    """

    pplogger = logging.getLogger(__name__)

    pplogger.info('Object type is ' + str(configs['objecttype']))

    pplogger.info('Pointing simulation result format is: ' + configs['pointingFormat']) 
    pplogger.info('Pointing simulation result path is: ' + configs['pointingdatabase'])
    pplogger.info('Pointing simulation result required query is: ' +  configs['ppdbquery']) 

    pplogger.info('The main filter in which brightness is defined is ' + configs['observing_filters'][0])
    othcs=' '.join(str(e) for e in configs['othercolours'])
    pplogger.info('The colour indices included in the simulation are ' + othcs)
    rescs=' '.join(str(f) for f in configs['observing_filters'])
    pplogger.info('Hence, the filters included in the post-processing results are ' + rescs)

    pplogger.info('The apparent brightness is calculated using the following phase function model: ' + configs['phasefunction'])
	
    if (configs['trailingLossesOn'] == True):
        pplogger.info('Computation of trailing losses is switched ON.')
    else:
        pplogger.info('Computation of trailing losses is switched OFF.')

    if (configs['cameraModel'] == 'footprint'):
        pplogger.info('Footprint is modelled after the actual camera footprint.')
        pplogger.info('Loading camera footprint from ' + configs['footprintPath'])
        pplogger.info('The filling factor has been set to ' + str(configs["fillfactor"]))
    else:
        pplogger.info('Footprint is circular')
        pplogger.info('The filling factor for the circular footprint is ' + str(configs["fillfactor"]))
	
    if configs['brightLimit']: pplogger.info('The upper brightness limit is ' + str(configs['brightLimit']))
    else: pplogger.info('Brightness limit is turned off.')

    if configs['SNRLimit']: pplogger.info('The lower SNR limit is ' + str(configs['SNRLimit']))
    else: pplogger.info('SNR limit is turned off.')
	
    if configs['SSPFiltering']:	
        pplogger.info('Solar System Processing filtering is turned on.')
        pplogger.info('For Solar System Processing, the fractional detection efficiency is ' + str(configs["SSPDetectionEfficiency"]))
        pplogger.info('For Solar System Processing, the minimum required number of observations in a tracklet is ' + str(configs['minTracklet']))
        pplogger.info('For Solar System Processing, the minimum required number of tracklets is ' + str(configs['noTracklets']))
        pplogger.info('For Solar System Processing, the maximum interval of time in days of tracklets to be contained in is ' + str(configs['trackletInterval']))
        pplogger.info('For Solar System Processing, the minimum angular separation between observations in arcseconds is ' + str(configs['inSepThreshold']))
    else:
        pplogger.info('Solar System Processing filtering is turned off.')

def PPFindFileOrExit(arg_fn, argname):
    """
    Author: Steph Merritt

    Description: Checks to see if the filename given by arg_fn actually exists. If it doesn't,
    this fails gracefully and exits to the command line.

    Mandatory input:	string, arg_fn, string filename passed by command line argument
                        string, argname,  name/flag of the argument printed in error message

    Output:				string, arg_fn unchanged
    """

    pplogger = logging.getLogger(__name__)

    if os.path.exists(arg_fn):
        return arg_fn
    else:
        pplogger.error('ERROR: filename {} supplied for {} argument does not exist.'.format(arg_fn, argname))
        sys.exit('ERROR: filename {} supplied for {} argument does not exist.'.format(arg_fn, argname))


def PPCMDLineParser(parser):
	"""
	Author: Steph Merritt
	
	Description: Parses the command line arguments, makes sure the filenames given actually exist,
	then stores them in a single dict.
	
	Will only look for the comet parameters file if it's actually given at the command line.
	
	Mandatory input:	ArgumentParser object, parser, of command line arguments
	
	output:				dictionary of variables taken from command line arguments
	
	"""

	args = parser.parse_args()

	cmd_args_dict = {}
	
	cmd_args_dict['paramsinput'] = PPFindFileOrExit(args.l, '-l --params')
	cmd_args_dict['orbinfile'] = PPFindFileOrExit(args.o, '-o --orbit')
	cmd_args_dict['oifoutput'] = PPFindFileOrExit(args.p, '-p, --pointing')
	cmd_args_dict['configfile'] = PPFindFileOrExit(args.c, '-c, --config')
	
	if args.m: cmd_args_dict['cometinput'] = PPFindFileOrExit(args.m, '-m, --comet') 
    
	cmd_args_dict['makeIntermediatePointingDatabase']=bool(args.d)
	cmd_args_dict['surveyname'] = args.s

	return cmd_args_dict
	
	
def PPWriteOutput(configs, observations, endChunk):
	"""
	Author: Steph Merritt
	
	Description: Writes out the output in the format specified in the config file.
	
	Mandatory input:	dict, configs, dictionary of config variables created by PPConfigFileParser
						pandas DataFrame, observations, table of observations for output
	"""
	
	pplogger = logging.getLogger(__name__)
	
	pplogger.info('Constructing output path...')
	if (configs['outputformat'] == 'csv'):
		outputsuffix='.csv'
		out= configs['outpath'] + configs['outfilestem'] + outputsuffix
		pplogger.info('Output to CSV file...')
		observations=PPOutWriteCSV.PPOutWriteCSV(observations,out)
	
	elif ((configs['outputformat'] == 'separatelyCSV') or (configs['outputformat'] == 'separatelyCsv') or (configs['outputformat'] == 'separatelycsv')):
		outputsuffix='.csv'
		objid_list = observations['ObjID'].unique().tolist() 
		pplogger.info('Output to ' + str(len(objid_list)) + ' separate output CSV files...')
		i=0
		while(i<len(objid_list)):
			single_object_df=pd.DataFrame(observations[observations['ObjID'] == objid_list[i]])
			out=configs['outpath'] + str(objid_list[i]) + '_' + configs['outfilestem'] + outputsuffix
			obsi=PPOutWriteCSV.PPOutWriteCSV(single_object_df,out)
			i=i+1	
	
	elif (configs['outputformat'] == 'sqlite3'):
		outputsuffix='.db'
		out= configs['outpath'] + configs['outfilestem'] + outputsuffix
		pplogger.info('Output to sqlite3 database...')
		observations=PPOutWriteSqlite3.PPOutWriteSqlite3(observations,out)   
	elif (configs['outputformat'] == 'hdf5' or configs['outputformat']=='HDF5'):
		outputsuffix=".h5"   
		out=configs['outpath'] + configs['outfilestem'] + outputsuffix
		pplogger.info('Output to HDF5 binary file...')
		observations=PPOutWriteHDF5.PPOutWriteHDF5(observations,out,str(endChunk))
		

def PPReadAllInput(cmd_args, configs, filterpointing, startChunk, incrStep):
    """
    Author: Steph Merritt

    Description: Reads in the simulation data and the orbit and physical parameter files, and then
    joins them with the pointing database to create a single Pandas dataframe of simulation
    data with all necessary orbit, physical parameter and pointing information.

    Mandatory input:	dict, cmd_args, dictionary of command line variables created by PPCMDLineParser
                        dict, configs, dictionary of config variables created by PPConfigFileParser
                        pandas DataFrame, filterpointing, pointing database
                        int, startChunk, start of chunk
                        int, incrStep, size of chunk

    Output:             pandas Dataframe, observations, dataframe of simulation data with all
                    necessary orbit, physical parameter and pointing information.
    """

    pplogger = logging.getLogger(__name__)

    pplogger.info('Reading input orbit file: ' + cmd_args['orbinfile'])
    padaor=PPReadOrbitFile.PPReadOrbitFile(cmd_args['orbinfile'], startChunk, incrStep, configs['filesep'])

    pplogger.info('Reading input physical parameters: ' + cmd_args['paramsinput'])
    padacl=PPReadPhysicalParameters.PPReadPhysicalParameters(cmd_args['paramsinput'], startChunk, incrStep, configs['filesep'])
    if (configs['objecttype'] == 'comet'):
        pplogger.info('Reading cometary parameters: ' + cmd_args['cometinput'])
        padaco=PPReadCometaryInput.PPReadCometaryInput(cmd_args['cometinput'], startChunk, incrStep, configs['filesep'])

    objid_list = padacl['ObjID'].unique().tolist() 

    # write pointing history to database
    # select obj_id rows from tables 

    if (cmd_args['makeIntermediatePointingDatabase'] == True):
        # read from intermediate database
        padafr=PPReadIntermDatabase.PPReadIntermDatabase('./data/interm.db', objid_list)
    else:   
        try: 
            pplogger.info('Reading input pointing history: ' + cmd_args['oifoutput'])
            padafr=PPReadEphemerides.PPReadEphemerides(cmd_args['oifoutput'], configs['ephemerides_type'], configs["pointingFormat"])
        
            padafr=padafr[padafr['ObjID'].isin(objid_list)]

        except MemoryError:
            pplogger.error('ERROR: insufficient memory. Try to run with -d True or reduce sizeSerialChunk.')
            sys.exit('ERROR: insufficient memory. Try to run with -d True or reduce sizeSerialChunk.')


    pplogger.info('Checking if orbit, brightness, physical parameters and pointing simulation input files match...')
    PPCheckOrbitAndPhysicalParametersMatching.PPCheckOrbitAndPhysicalParametersMatching(padaor,padacl,padafr)

    if (configs['objecttype'] == 'comet'):
        PPCheckOrbitAndPhysicalParametersMatching.PPCheckOrbitAndPhysicalParametersMatching(padaor,padaco,padafr)
     
    pplogger.info('Joining physical parameters and orbital data with simulation data...')       
    observations=PPJoinPhysicalParametersPointing.PPJoinPhysicalParametersPointing(padafr,padacl)
    observations=PPJoinOrbitalData.PPJoinOrbitalData(observations,padaor)
    if (configs['objecttype'] == 'comet'):
        pplogger.info('Joining cometary data...')
        observations=PPJoinPhysicalParametersPointing.PPJoinPhysicalParametersPointing(observations,padaco)

    pplogger.info('Joining info from pointing database with simulation data and dropping observations in non-requested filters...')
    observations = PPMatchPointingToObservations.PPMatchPointingToObservations(observations, filterpointing)   

    return observations