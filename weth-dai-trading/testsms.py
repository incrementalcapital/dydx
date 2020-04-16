#!/usr/bin/env python3


import json
import boto3

# Create AWS SNS client
snsclient = boto3.client('sns')

# Send SMS message.
response = snsclient.publish(
    PhoneNumber='+12062270634',
    Message='This is a test SMS message.',
)

# Display SMS execution details
jsondata = json.dumps(
    response,
    sort_keys=True,
    indent=4,
    separators=(',', ': ')
)
print ( jsondata )
