#!/usr/bin/env python3


import json
import logging
from decimal import Decimal

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from logger import logger
from credentials import client

# Define best price function
# Return market / limit price
def bestorders( tradingpair, quotetick ):
    # Get the orderbook for the trading pair specified
    orderbook = client.get_orderbook( market = tradingpair )

    # Define best ask and best bid values in the market
    marketask = orderbook["bids"][0]["price"]
    marketbid = orderbook["asks"][0]["price"]

    # Define most competitive ask and bid that can be posted to the orderbook
    if Decimal( marketbid ) - Decimal( marketask ) > Decimal( quotetick ):
        limitask = Decimal( marketask ) + Decimal( quotetick )
        limitbid = Decimal( marketbid ) - Decimal( quotetick )
    else:
        limitask = marketask
        limitbid = marketbid

    # Return the best ask and best bid
    # In the orderbook of the trading pair
    # Also, return the most competitive limit orders
    return ( marketask, marketbid, limitask, limitbid )


# Define post-only ask
# In other words, limit ask
def postask( price, quantity ):

    logger.debug ( f'Asking {price} DAI/ETH for {quantity} ETH.' )
    ask = Decimal(price)
    amount = Decimal(quantity)

    # Ask.
    try:
        # Submit order to dYdX.
        submission = client.place_order(
            market=consts.PAIR_WETH_DAI,
            side=consts.SIDE_SELL,
            amount=utils.token_to_wei(amount, consts.MARKET_WETH),
            price=ask,
            fillOrKill=False,
            postOnly=True
        )
    except Exception as e:
        # Throw a critical error notice if anything funky occurs.
        logger.critical(f'{e}', exc_info=True)
        return 'ERROR'

    # Write the dYdX response to the submission to the logs.
    jsondata = json.dumps( submission, sort_keys=True, indent=4, separators=(',', ': ') )
    logger.debug ( f'Order submission:\n{jsondata}' )

    # Return results of the submission to BUY ETH
    return submission


# Define post-only bid
# In other words, limit bid
def postbid( price, quantity ):

    logger.debug ( f'Bidding at {price} DAI/ETH for {quantity} ETH.' )
    bid = Decimal(price)
    amount = Decimal(quantity)

    # Bid.
    try:
        # Submit order to dYdX.
        submission = client.place_order(
            market=consts.PAIR_WETH_DAI,
            side=consts.SIDE_BUY,
            amount=utils.token_to_wei(amount, consts.MARKET_WETH),
            price=bid,
            fillOrKill=False,
            postOnly=True
        )
    except Exception as e:
        # Throw a critical error notice if anything funky occurs.
        logger.critical(f'{e}', exc_info=True)
        return 'ERROR'

    # Write the dYdX response to the submission to the logs.
    jsondata = json.dumps( submission, sort_keys=True, indent=4, separators=(',', ': ') )
    logger.debug ( f'Order submission:\n{jsondata}' )

    # Return results of the submission to BUY ETH
    return submission
