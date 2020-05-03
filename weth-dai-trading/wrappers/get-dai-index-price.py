#!/usr/bin/env python3

from decimal import Decimal

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from credentials import client


# Get dYdX index price for ETH
rawdata = client.eth.solo.get_oracle_price( consts.MARKET_DAI )
pricedata = Decimal(rawdata) * Decimal( 10**(consts.DECIMALS_DAI) )
indexprice = Decimal(pricedata)

# Format balance using DECIMAL information for the asset
print ( f'{indexprice:28.5} USD/DAI' )
