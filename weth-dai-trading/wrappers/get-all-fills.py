#!/usr/bin/env python3

import json
from decimal import Decimal

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from credentials import client


# Get all fills from the orderbook
resultlimit = Decimal("2")
all_fills = client.get_fills(
    market=['WETH-DAI'], # 'DAI-WETH' side of the book is not included
    limit=resultlimit,  # optional
    startingBefore=None  # optional
)

jsondata = json.dumps( all_fills, sort_keys=True, indent=4, separators=(',', ': ') )

print ( jsondata )
print ( "The results are limited to the most recent " , resultlimit , " orders.")
