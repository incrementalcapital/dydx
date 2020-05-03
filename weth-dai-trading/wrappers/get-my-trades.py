#!/usr/bin/env python3

import json

import dydx.constants as consts
import dydx.util as utils

from credentials import client


# Get trades created by my account
my_trades = client.get_my_trades(
    market=['WETH-DAI'],
    limit=None,  # optional
    startingBefore=None  # optional
)

jsondata = json.dumps( my_trades, sort_keys=True, indent=4, separators=(',', ': ') )

print ( jsondata )
