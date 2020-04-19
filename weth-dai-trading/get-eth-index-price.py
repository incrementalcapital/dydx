#!/usr/bin/env python3

from decimal import Decimal

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from credentials import client


# Get dYdX index price for ETH
rawdata = client.eth.solo.get_oracle_price( consts.MARKET_WETH )
pricedata = Decimal(rawdata) * Decimal( 10**(consts.DECIMALS_WETH) )
indexprice = Decimal(pricedata)

# Format balance using DECIMAL information for the asset
print ( asset, "is" , indexprice.quantize( Decimal("0.0001") ), "dollars." )
