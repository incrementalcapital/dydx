#!/usr/bin/env python3


import json
import boto3

from logger import logger

# Create AWS SNS client
snsclient = boto3.client('sns')

# Define alert function
def smsalert( message ):
    # Send message via SMS.
    snsresponse = snsclient.publish( PhoneNumber='+15108045618', Message=message )
    responseout = json.dumps( snsresponse, sort_keys=True, indent=4, separators=(',', ': ') )
    logger.debug ( responseout )
    # Log SMS execution details
