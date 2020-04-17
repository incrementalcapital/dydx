#!/usr/bin/env python3

import json
from decimal import Decimal

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from logger import logger
from credentials import client
from orderer import bestorders


# Define a quanity of ETH well in excess of 5X margin
bidquantity = 10000

# Get WETH-DAI market information
market = client.get_market( market='WETH-DAI' )
quotetick = market["market"]["minimumTickSize"]

# Get best order pricing information
orderinginfo = bestorders( 'WETH-DAI', quotetick )
logger.debug ( f'{orderinginfo[0]} is the best market ask.' )
logger.debug ( f'{orderinginfo[1]} is the best market bid.' )
logger.debug ( f'{orderinginfo[2]} is the best limit ask.' )
logger.debug ( f'{orderinginfo[3]} is the best limit ask.' )

try:
    # Create order to BUY more ETH than collateral allows
    created_order = client.place_order(
        market=consts.PAIR_WETH_DAI,
        side=consts.SIDE_BUY,
        amount=utils.token_to_wei(bidquantity, consts.MARKET_WETH),
        price=orderinginfo[3].quantize( Decimal( quotetick ) ),
        fillOrKill=False,
        postOnly=False
    )
    # Log order submission's response from dYdX
    jsondata = json.dumps(
        created_order,
        sort_keys=True,
        indent=4,
        separators=(',', ': ')
    )
    logger.debug ( jsondata )
    # Display order information
    logger.info ( f'Ordered {amount} ETH at {orderinginfo[3].quantize( Decimal( quotetick ) )} DAI/ETH.' )

except Exception as e:
    logger.critical("Exception occurred", exc_info=True)
