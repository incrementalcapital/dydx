#!/usr/bin/env python3


from decimal import Decimal

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

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
        # Create order to SELL ETH
        placed_ask = client.place_order(
            market=consts.PAIR_WETH_DAI,
            side=consts.SIDE_SELL,
            amount=utils.token_to_wei(quantity, consts.MARKET_WETH),
            price=price,
            fillOrKill=False,
            postOnly=True
        )
        return placed_ask


# Define post-only bid
# In other words, limit bid
def postbid( price, quantity ):
        # Submit the order to BUY ETH
        placed_bid = client.place_order(
            market=consts.PAIR_WETH_DAI,
            side=consts.SIDE_BUY,
            amount=utils.token_to_wei(quantity, consts.MARKET_WETH),
            price=price,
            fillOrKill=False,
            postOnly=True
        )
        return placed_bid
