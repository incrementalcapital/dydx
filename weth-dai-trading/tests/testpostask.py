#!/usr/bin/env python3


from decimal import Decimal

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from logger import logger
from credentials import client
from orderer import bestorders
from orderer import postask


# Get WETH-DAI market information
market = client.get_market( market='WETH-DAI' )
quotetick = market["market"]["minimumTickSize"]

# Determine most competitive ask limit price
orderinginfo = bestorders( 'WETH-DAI', quotetick )
logger.debug ( f'{orderinginfo[0]} is the best market ask.' )
logger.debug ( f'{orderinginfo[1]} is the best market bid.' )
logger.debug ( f'{orderinginfo[2]} is the best limit ask.' )
logger.debug ( f'{orderinginfo[3]} is the best limit bid.' )

# Set ask amount to the minimum allowable trade size (no associated fees)
quantity = consts.SMALL_TRADE_SIZE_WETH / (10 ** consts.DECIMALS_WETH)

try:
    # Submit order to dYdX
    submission = postask( orderinginfo[2].quantize( Decimal( quotetick ) ), quantity )

except Exception as e:
    # Throw a critical error notice if anything funky occurs
    logger.critical("Exception occurred", exc_info=True)

# Write the submission's response to the logs
logger.debug ( f'order submission:\n{submission}' )
# Display submission information to the console
logger.info ( f'Selling {quantity} ETH at {orderinginfo[3].quantize( Decimal( quotetick ) )} DAI/ETH.' )
