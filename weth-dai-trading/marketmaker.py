#!/usr/bin/env python3


import os
import json
import time
import logging
from web3 import Web3
from decimal import Decimal

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from credentials import client


# Create custom logger
logger = logging.getLogger('tradelogger')
logger.setLevel(logging.DEBUG)
script = os.path.splitext(__file__)
outlog = '/tmp/' + script[0] + '.out'
errlog = '/tmp/' + script[0] + '.err'
# Create console and file handlers
consolehandler = logging.StreamHandler()
fileouthandler = logging.FileHandler(outlog)
fileerrhandler = logging.FileHandler(errlog)
consolehandler.setLevel(logging.INFO)
fileouthandler.setLevel(logging.DEBUG)
fileerrhandler.setLevel(logging.WARNING)
# Create formatters and add it to handlers
consoleformat = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
fileoutformat = logging.Formatter('%(asctime)s PID[%(process)d]:  %(levelname)s  -  %(message)s')
fileerrformat = logging.Formatter('%(asctime)s PID[%(process)d]:  %(levelname)s  -  %(message)s  [from %(name)s]')
consolehandler.setFormatter(consoleformat)
fileouthandler.setFormatter(fileoutformat)
fileerrhandler.setFormatter(fileerrformat)
# Add handlers to the logger
logger.addHandler(consolehandler)
logger.addHandler(fileouthandler)
logger.addHandler(fileerrhandler)


# Define the return on assets and price drop (pricetrigger) required for bidding
# Also define a stop limit ask and a stop market ask (just in case the price crashes)
# In addition, define target (mimimum) collateralization ratio and maximum leverage
# Note: to make a bid without waiting for the prices to fall, set the price trigger to 1
pricetrigger = Decimal( "0.99" )
logger.info ( f'pricetrigger = {100*pricetrigger:5.2f}%' )
# Submit a bid after a 1% drop in the ask price
requiredreturn = Decimal( "1.01" )
logger.info ( f'requiredreturn = {100*(requiredreturn-1):5.2f}%' )
# Submit an ask immediately after the bid is filled.
stoplimitask = Decimal( "0.99" )
logger.info ( f'stoplimitask = {100*stoplimitask:5.2f}%' )
# Break out of a loop waiting for the profitable ask to fill if the stop limit is triggered.
stopmarketask = Decimal( "0.98" )
logger.info ( f'stopmarketask = {100*stopmarketask:5.2f}%' )
# Break out of a loop waiting for the profitable ask to fill if the stop market is triggered.
maximumleverage = Decimal( "5" )
logger.info ( f'maximumleverage = {maximumleverage:5.2f}X' )
# 5X constants established by dYdX (note that it is 4X for a SHORT)
minimumcollateralization = Decimal( "1.25" )
logger.info ( f'minimumcollateralization = {100*minimumcollateralization:5.2f}%' )
# dYdX accounts must be overcollateralized at the ratio of 125%.
# Note that positions are liquidated at 115%.
# However, the target collateralization should reflect risk tolerance.
# For example, a cautious trader may feel comfortable using a target of 150%.
# Or the trader may prefer to be overcollateralized at 200% during periods of high volatility.


# Define best price function
# Return market / limit price
def bestprices( tradingpair, quotetick ):
    # Get the orderbook for the trading pair specified
    orderbook = client.get_orderbook( market = tradingpair )

    # Define best ask and best bid values in the market
    marketask = orderbook["asks"][0]["price"]
    marketbid = orderbook["bids"][0]["price"]

    # Define most competitive limit ask
    if Decimal( marketask ) - Decimal( marketbid ) > Decimal( quotetick ):
        rawbid = Decimal( marketask ) - Decimal( quotetick )
        limitbid = rawbid.quantize( Decimal( quotetick ) )
    else:
        rawbid = Decimal( marketbid )
        limitbid = rawbid.quantize( Decimal( quotetick ) )

    # Define most competitive limit bid
    if Decimal( marketask ) - Decimal(marketbid) > Decimal(quotetick):
        rawask = Decimal( marketbid ) + Decimal( quotetick )
        limitask = rawask.quantize( Decimal( quotetick ) )
    else:
        rawask = Decimal( marketask )
        limitask = rawask.quantize( Decimal( quotetick ) )

    # Return the best ask and best bid
    # In the orderbook of the trading pair
    # Also, return the most competitive limit orders
    return ( marketask, marketbid, limitask, limitbid )


# Get dYdX markets and define market constants
markets = client.get_markets()
daiquotetick = markets["markets"]["WETH-DAI"]["minimumTickSize"]
daidecimals = markets["markets"]["WETH-DAI"]["quoteCurrency"]["decimals"]
daiassetid = markets["markets"]["WETH-DAI"]["quoteCurrency"]["soloMarketId"]
usdcdecimals = markets["markets"]["WETH-USDC"]["quoteCurrency"]["decimals"]
usdcassetid = markets["markets"]["WETH-USDC"]["quoteCurrency"]["soloMarketId"]
wethdecimals = markets["markets"]["WETH-DAI"]["baseCurrency"]["decimals"]
wethassetid = markets["markets"]["WETH-DAI"]["baseCurrency"]["soloMarketId"]


# Start market maker
while True:
    logger.info( f'\n\n\nBegin providing liquidity for those shorting ETH...' )

    # Get best ask and determine price trigger
    bookprices = bestprices( 'WETH-DAI', daiquotetick )
    presentask = Decimal( bookprices[0] )
    triggerask = Decimal( presentask ) * Decimal ( pricetrigger )
    logger.info ( f'The lowest ask in the orderbook is: {presentask:10.4f} DAI/ETH' )
    logger.info ( f'To trigger a bid, the lowest ask in the orderbook must fall below: {triggerask:10.4f} DAI/ETH' )
    logger.info ( f'Enter a loop to monitor the market...' )
    # Loop until the ask drops below the trigger price
    while Decimal(presentask) > Decimal(triggerask):
        logger.debug ( f'{presentask:10.4f} > {triggerask:10.4f}' )
        # Sleep ten seconds before checking updating the present price
        time.sleep(10)
        # Update prices
        bookprices = bestprices( 'WETH-DAI', daiquotetick )
        presentask = Decimal(bookprices[0])
        # If the present price is below the trigger price this loop ends
    logger.info ( f'The lowest ask on the market [{presentask:10.4f}] is less than (or equals) the trigger price: {triggerask:10.4f}' )


    # Get dYdX index price for DAI returned in US dollar terms
    # dYdX uses price oracles for DAI
    oracleprice = client.eth.get_oracle_price( daiassetid )
    normalprice = Decimal(oracleprice) * Decimal( 10**(daidecimals) )
    daiusdprice = Decimal(normalprice)
    logger.debug( f'The oracles says 1 DAI is: {daiusdprice:10.4f} US dollars')


    # Get dYdX account balances
    balances = client.eth.get_my_balances()
    # Determine overcollateralized collateral (USDC asset balance in DAI terms)
    # And DAI balance to determine the maximum amount of DAI borrowable
    # Do not use the Oracle Price for ETH because it is inaccurate for present debt calculations
    ethbalance = Decimal( balances[wethassetid] / (10**wethdecimals) ) * Decimal(presentask)
    usdbalance = Decimal( balances[usdcassetid] / (10**usdcdecimals) ) / Decimal(daiusdprice)
    daibalance = Decimal( balances[daiassetid] / (10**daidecimals) )
    # Determine the DAI value of the dYdX account and the margin that affords
    # Calculate the maximum additional debt allowed (in DAI terms)
    dydxaccount = Decimal(ethbalance) + Decimal(usdbalance) + Decimal(daibalance)
    totalmargin = Decimal(dydxaccount) / Decimal(minimumcollateralization)
    maximumdebt = Decimal(totalmargin) * Decimal(maximumleverage)
    # Define pertinent DAI liabilities
    if Decimal( daibalance ) < 0:
        liabilities = abs( daibalance )
    else:
        liabilities = 0
    logger.debug( f'This dYdX account has DAI liabilities of: {liabilities:10.4f} DAI')
    # Determine the available debt accessible to the dYdX account
    availabledebt = Decimal(maximumdebt) - Decimal(liabilities)
    # Note: going long on ETH with DAI means having to remove the existing DAI liabilities in the calculation
    logger.info ( f'This dYdX account has a balance of {dydxaccount:10.4f} [in DAI terms].')
    logger.info ( f'Presently has {ethbalance:10.4f} ETH [a negative sign indicates debt].')
    logger.info ( f'Presently has {usdbalance:10.4f} USD [a negative sign indicates debt].')
    logger.info ( f'Presently has {daibalance:10.4f} DAI [a negative sign indicates debt].')
    logger.info ( f'dYdX allows {100/minimumcollateralization:5.2f}% for trades on margin.')
    logger.info ( f'The maximum possible liability allowed is now {maximumdebt:10.4f} DAI.')
    logger.info ( f'Thanks the {maximumleverage:5.2f}X leverage on {totalmargin:5.2f} DAI.')
    logger.info ( f'The debt available to this dYdX account is: {availabledebt:10.4f} DAI.')


    # Determine most competitive bid price and amount
    # Based on the debt remaining and present market values
    bookpricing = bestprices( 'WETH-DAI', daiquotetick )
    greatestbid = bookpricing[3]
    bidquantity = Decimal(availabledebt) / Decimal(greatestbid)
    # Submit the order to BUY ETH
    placed_bid = client.place_order(
        market=consts.PAIR_WETH_DAI,
        side=consts.SIDE_BUY,
        amount=utils.token_to_wei(bidquantity, consts.MARKET_WETH),
        price=greatestbid,
        fillOrKill=False,
        postOnly=False
    )
    # Log order information to console
    jsondata = json.dumps( placed_bid, sort_keys=True, indent=4, separators=(',', ': ') )
    logger.info ( jsondata )


    # Loop until the bid is filled
    while True:
        # Give a status update on the get_orderbook
        orderbookpricing = bestprices( 'WETH-DAI', daiquotetick )
        topask = orderbookpricing[0]
        topbid = orderbookpricing[1]
        logger.debug( f'Submitted a bid for {bidquantity} ETH at {greatestbid}. The best bid now is {topbid} and the best ask is {topask}.')
        # Give the bid placed five seconds to fill
        time.sleep(5)
        # Get fills
        lastfill = client.get_my_fills(market=['WETH-DAI'],limit=1)
        if lastfill["fills"][0]["orderId"] == placed_bid["order"]["id"]:
            logger.info ( 'Order %s was filled.', placed_bid["order"]["id"])
            break


    # Place ask to close the position opened by the bid
    # that returns 100 basis points
    askprice = Decimal( greatestbid ) * Decimal( requiredreturn )
    quantity = bidquantity
    # Create order to SELL ETH
    placed_ask = client.place_order(
        market=consts.PAIR_WETH_DAI,
        side=consts.SIDE_SELL,
        amount=utils.token_to_wei(quantity, consts.MARKET_WETH),
        price=askprice.quantize( Decimal(daiquotetick) ),
        fillOrKill=False,
        postOnly=False
    )
    # Display order information
    jsondata = json.dumps( placed_ask, sort_keys=True, indent=4, separators=(',', ': ') )
    logger.info ( jsondata )


    # Define stop market and stop limit sell order prices
    sellthreshold = Decimal( greatestbid ) * Decimal( stoplimitask )
    dumpthreshold = Decimal( greatestbid ) * Decimal( stopmarketask )
    logger.info( f'From this point forth, if the submitted ask is not filled and the price drops below {sellthreshold:10.4f} submit a stop limit order.')
    logger.info( f'From this point forth, if the submitted ask is not filled and the price drops below {dumpthreshold:10.4f} issue a stop market order.')
    # Enter loop
    while True:
        # Check the status of the submitted ask
        submittedask = client.get_order( orderId=placed_ask["order"]["id"] )
        if submittedask["order"]["status"] == "FILLED":
            # Exit: End the loop and exit.
            logger.info ( f'Order {submittedask["order"]["id"]} was filled at: {submittedask["order"]["price"]} DAI/ETH.')
            break
        else:
            # Sleep
            # Then check price
            time.sleep(5)
            bookprices = bestprices( 'WETH-DAI', daiquotetick )
            bookmarket = Decimal( bookprices[1] )
            limitprice = Decimal( bookprices[2] )
            logger.debug ( f'The highest bid in the orderbook is {bookmarket-sellthreshold:10.4f} DAI above the stop limit {sellthreshold:10.4f}, \
                                                             and {bookmarket-dumpthreshold:10.4f} DAI above the stop market {dumpthreshold:10.4f}.' )

            # If the present price is below the trigger price this loop ends
            if Decimal( bookmarket ) < Decimal( dumpthreshold ):
                logger.info ( f'The highest bid in the orderbook [{bookmarket:10.4f}] just fell below the stop market sell threshold: {dumpthreshold:10.4f}')
                # Create order to SELL ETH
                placed_stop = client.place_order(
                    market=consts.PAIR_WETH_DAI,
                    side=consts.SIDE_SELL,
                    amount=utils.token_to_wei(quantity, consts.MARKET_WETH),
                    price=bookmarket.quantize( Decimal(daiquotetick) ),
                    fillOrKill=False,
                    postOnly=False
                )
                # Display order information
                jsondata = json.dumps( placed_stop, sort_keys=True, indent=4, separators=(',', ': ') )
                logger.info ( jsondata )
                # Cancel the previously submitted ask then exit the loop.
                logger.info ( "Cancelling order: %s", submittedask["order"]["id"] )
                canceledask = client.cancel_order( hash=placed_ask["order"]["id"] )
                # Display order cancel information
                jsondata = json.dumps( canceledask, sort_keys=True, indent=4, separators=(',', ': ') )
                logger.info ( jsondata )
                # Exit loop
                break
            elif Decimal( dumpthreshold ) < Decimal( bookmarket ) < Decimal( sellthreshold ):
                logger.info ( f'The highest bid in the orderbook [{bookmarket:10.4f}] just fell below the stop limit sell threshold: {sellthreshold:10.4f}')
                # Create order to SELL ETH
                placed_stop = client.place_order(
                    market=consts.PAIR_WETH_DAI,
                    side=consts.SIDE_SELL,
                    amount=utils.token_to_wei(quantity, consts.MARKET_WETH),
                    price=limitprice.quantize( Decimal(daiquotetick) ),
                    fillOrKill=False,
                    postOnly=False
                )
                # Display order information
                jsondata = json.dumps( placed_stop, sort_keys=True, indent=4, separators=(',', ': ') )
                logger.info ( jsondata )
                # Cancel the previously submitted ask then exit the loop.
                logger.info ( "Cancelling order: %s", submittedask["order"]["id"] )
                canceledask = client.cancel_order( hash=placed_ask["order"]["id"] )
                # Display order cancel information
                jsondata = json.dumps( canceledask, sort_keys=True, indent=4, separators=(',', ': ') )
                logger.info ( jsondata )
                # Exit loop
                break


    # Withdraw DAI gains if any
    # Check dYdX DAI account balance
    balances = client.eth.get_my_balances()
    daibalance = Decimal( balances[daiassetid] / (10**daidecimals) )
    # Since withdrawals go to the blockchain and need GAS, only withdrawal if gains exceed $2
    if Decimal(daibalance) > 2:
        withdrawalhash = client.eth.solo.withdraw_to_zero( market=consts.MARKET_DAI )
        # Display deposit confirmation
        logger.info ( f'Depositing {daibalance:10.4f} DAI to the wallet associated with this dYdX account...' )
        receipt = client.eth.get_receipt( withdrawalhash )
        web3out = Web3.toJSON( receipt )
        logger.debug ( web3out )
        logger.info ( 'Done.' )


    logger.info( f'End of liquidity provision.\n\n\n' )
