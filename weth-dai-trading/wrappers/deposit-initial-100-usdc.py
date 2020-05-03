#!/usr/bin/env python3


import sys
import json

from web3 import Web3

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from credentials import client


# Set Allowance [must only be called once EVER]
deposithash = client.eth.solo.set_allowance(market=consts.MARKET_USDC)
receipt = client.eth.get_receipt(deposithash)

# Specify deposit amount
depositamount = 100

try:
    # Deposit USDC
    deposithash = client.eth.solo.deposit(
        market=consts.MARKET_USDC,
        wei=utils.token_to_wei( depositamount, consts.MARKET_USDC )
    )

except Exception as e:
    # Throw a critical error notice if anything funky occurs
    print ( f'Exception occurred:\n\n{e}\n' )
    sys.exit(0)

# Display withdrawal information
receipt = client.eth.get_receipt( deposithash )
web3out = Web3.toJSON( receipt )
strings = str( web3out )
dataout = json.loads( strings )
jsonout = json.dumps( dataout, sort_keys=True, indent=4, separators=(',', ': ') )
print (jsonout)
