#!/usr/bin/env python3

import sys
import json

from web3 import Web3

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from credentials import client


try:
    # Withdraw all DAI
    withdrawalhash = client.eth.solo.withdraw_to_zero( market=consts.MARKET_DAI )

except Exception as e:
    # Throw a critical error notice if anything funky occurs
    print ( f'Exception occurred:\n\n{e}\n' )
    sys.exit(0)

# Display withdrawal information
receipt = client.eth.get_receipt( withdrawalhash )
web3out = Web3.toJSON( receipt )
strings = str( web3out )
dataout = json.loads( strings )
jsonout = json.dumps( dataout, sort_keys=True, indent=4, separators=(',', ': ') )
print (jsonout)
