#!/usr/bin/env python3


import os
import logging


# Create custom logger
logger = logging.getLogger('tradelogger')
logger.setLevel(logging.DEBUG)
script = os.path.splitext(__file__)
outlog = '/tmp/' + script[0] + '.out'
errlog = '/tmp/' + script[0] + '.err'
# Create console and file handlers
consolehandler = logging.StreamHandler()
fileouthandler = logging.FileHandler(outlog)
fileerrhandler = logging.FileHandler(errlog)
consolehandler.setLevel(logging.INFO)
fileouthandler.setLevel(logging.DEBUG)
fileerrhandler.setLevel(logging.WARNING)
# Create formatters and add it to handlers
consoleformat = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
fileoutformat = logging.Formatter('%(asctime)s PID[%(process)d]:  %(levelname)s  -  %(message)s')
fileerrformat = logging.Formatter('%(asctime)s PID[%(process)d]:  %(levelname)s  -  %(message)s  [from %(name)s]')
consolehandler.setFormatter(consoleformat)
fileouthandler.setFormatter(fileoutformat)
fileerrhandler.setFormatter(fileerrformat)
# Add handlers to the logger
logger.addHandler(consolehandler)
logger.addHandler(fileouthandler)
logger.addHandler(fileerrhandler)


# Generate log messages
logger.debug('This is a debug message')
logger.info('This is an info message')
logger.warning('This is a warning message')
logger.error('This is an error message')
logger.critical('This is a critical message')
