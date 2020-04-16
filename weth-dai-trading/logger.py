#!/usr/bin/env python3


import os
import __main__
import logging


# Create custom logger
logger = logging.getLogger('tradelogger')
logger.setLevel(logging.DEBUG)
ospath = os.path.basename(__main__.__file__)
script = os.path.splitext(ospath)
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
consoleformat = logging.Formatter('%(name)s - %(levelname)-8s - %(message)s')
fileoutformat = logging.Formatter('%(asctime)s PID[%(process)d]:  %(levelname)-8s [%(name)-11s] %(message)s')
fileerrformat = logging.Formatter('%(asctime)s PID[%(process)d]:  %(levelname)-8s [%(name)-11s] %(message)s')
consolehandler.setFormatter(consoleformat)
fileouthandler.setFormatter(fileoutformat)
fileerrhandler.setFormatter(fileerrformat)

# Add handlers to the logger
logger.addHandler(consolehandler)
logger.addHandler(fileouthandler)
logger.addHandler(fileerrhandler)
