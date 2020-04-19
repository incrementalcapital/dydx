#!/usr/bin/env python3


import json
import time
from web3 import Web3
from decimal import Decimal

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from logger import logger
from orderer import postbid
from orderer import postask
from messenger import smsalert
from credentials import client
from orderer import bestorders
from creditcalculator import creditavailable


# Define the return on assets and price drop (pricetrigger) required for bidding
# Also define a stop limit ask and a stop market ask (just in case the price crashes)
# In addition, define target (mimimum) collateralization ratio and maximum leverage
# Note: to make a bid without waiting for the prices to fall, set the price trigger to 1
logger.info( f'Define execution parameters...' )
pricetrigger = 0.9999
logger.info ( f'pricetrigger = {100*pricetrigger:.2f}%' )
# Submit a bid after a 1% drop in the ask price
requiredreturn = 1.0013
logger.info ( f'requiredreturn = {100*(requiredreturn-1):.2f}%' )
# Submit an ask immediately after the bid is filled.
stoplimit = 0.99
logger.info ( f'stoplimit = {100*stoplimit:.2f}%' )
# Break out of a loop waiting for the profitable ask to fill if the stop limit is triggered.
appliedleverage = 4
logger.info ( f'appliedleverage = {appliedleverage:.2f}X' )
# The maximim leverage that can be applied going LONG is 5X.
# This is established by dYdX (note that it is 4X for a SHORT)
minimumcollateralization = 1.25
logger.info ( f'minimumcollateralization = {100*minimumcollateralization:.2f}%' )
logger.info( f'Execution parameters defined.\n\n\n\n' )
# dYdX accounts must be overcollateralized at the ratio of 125%.
# Note that positions are liquidated at 115%.
# However, the target collateralization should reflect risk tolerance.
# For example, a cautious trader may feel comfortable using a target of 150%.
# Or the trader may prefer to be overcollateralized at 200% during periods of high volatility.
markets = client.get_markets()
quotetick = Decimal( markets["markets"]["WETH-DAI"]["minimumTickSize"] )
# Defined dYdX market constant


# Start market maker
while True:
    logger.info( f'Begin providing liquidity for those shorting ETH...' )

    # Get best (top) ask and calculate trigger (marker)
    prices = bestorders( 'WETH-DAI', quotetick )
    topask = Decimal( prices[1] )
    marker = Decimal( topask ) * Decimal ( pricetrigger )
    oldask = topask
    logger.info ( f'The lowest ask in the orderbook is {topask:.4f} DAI/ETH' )
    logger.info ( f'To trigger a bid, the lowest ask in the orderbook must fall below {marker:.4f} DAI/ETH' )
    logger.info ( f'Enter a loop to monitor the market...' )
    # Loop until the ask drops below the trigger price
    while Decimal(topask) > Decimal(marker):
        # If the present price is higher than the old ask
        if Decimal(topask) > Decimal(oldask):
            # Redefine trigger
            marker = Decimal( topask ) * Decimal ( pricetrigger )
        logger.debug ( f'Best Ask [{topask:.4f}] > Trigger Price [{marker:.4f}]' )
        # Sleep ten seconds before checking updating the present price
        time.sleep(10)
        # Update prices
        prices = bestorders( 'WETH-DAI', quotetick )
        topask = Decimal( prices[1] )
        # If the present price is below the previously defined trigger price this loop essentially ends here
    logger.info ( f'The lowest ask on the market [{topask:.4f} DAI/ETH] is less than (or equals) the trigger price [{marker:.4f} DAI/ETH]' )


    # Get credit available
    availablecredit = creditavailable( appliedleverage )


    # Determine most competitive bid price and amount
    # Based on the debt remaining and present market values
    prices = bestorders( 'WETH-DAI', quotetick )
    bideth = Decimal( prices[3] )
    amount = Decimal( availablecredit ) / Decimal( prices[3] )
    cutoff = consts.SMALL_TRADE_SIZE_WETH / (10 ** consts.DECIMALS_WETH)
    if amount < cutoff:
        logger.debug ('Check account margin or leverage [presently {appliedleverage}X] used.')
        logger.debug ( f'Insufficient collateral. The bid {amount:.4f} is below {cutoff} ETH.' )
        logger.info( f'Unable to provide liquidity for those shorting ETH... Going to sleep for 10 hours.\n\n\n\n' )
        smsalert( f'Invalid bid quantity [{amount:.4f} DAI].' )
        time.sleep(36000)
        continue


    # Bid
    try:
        # Submit order to dYdX
        logger.debug ( f'Bidding {bideth.quantize( quotetick )} DAI/ETH for {amount:.4f} ETH.' )
        submission = postbid( bideth.quantize( quotetick ), amount )

    except Exception as e:
        # Throw a critical error notice if anything funky occurs
        logger.critical("Exception occurred", exc_info=True)

    # Write the submission's response to the logs
    jsondata = json.dumps( submission, sort_keys=True, indent=4, separators=(',', ': ') )
    logger.debug ( f'Order submission:\n{jsondata}' )
    # Report submission information via SMS
    smsalert( f'Bidding {bideth*amount:.4f} DAI for {amount:.4f} ETH.' )


    # Loop until the bid is filled
    while True:
        # Give a status update on the get_orderbook
        prices = bestorders( 'WETH-DAI', quotetick )
        topask = Decimal( prices[1] )
        topbid = Decimal( prices[0] )
        logger.debug( f'Bidding {bideth:.4f} DAI/ETH. The highest bid now is {topbid:.4f} DAI/ETH and the cheapest ask is {topask:.4f} DAI/ETH.')
        # Give the bid placed five seconds to fill
        time.sleep(5)
        # Get fills
        lastfill = client.get_my_fills(market=['WETH-DAI'],limit=1)
        if lastfill["fills"][0]["orderId"] == submission["order"]["id"]:
            logger.info ( 'Order %s was filled.', submission["order"]["id"])
            smsalert( f'Bid {bideth*amount:.4f} DAI for {amount:.4f} ETH.')
            break


    # Place ask to close the position opened by the bid
    # that returns 100 basis points
    askprice = Decimal( bideth ) * Decimal( requiredreturn )
    quantity = amount

    # Ask
    try:
        # Submit order to dYdX
        logger.debug ( f'Asking {askprice.quantize( quotetick )} DAI/ETH for {quantity:.4f} ETH.' )
        submission = postask( askprice.quantize( quotetick ), quantity )

    except Exception as e:
        # Throw a critical error notice if anything funky occurs
        logger.critical("Exception occurred", exc_info=True)

    # Write the submission's response to the logs
    jsondata = json.dumps( submission, sort_keys=True, indent=4, separators=(',', ': ') )
    logger.debug ( f'Order submission:\n{jsondata}' )
    # Report submission information via SMS
    smsalert( f'Bidding {askprice*quantity:.4f} DAI for {quantity:.4f} ETH.' )


    # Define stop limit sell order price
    # Right now the dYdX Python client does not support market orders
    # The dYdX stop order is based on the oracle price and it is unwieldy
    sellthreshold = Decimal( bideth ) * Decimal( stoplimit )
    logger.info( f'From this point forth, if the submitted ask is not filled and the price drops below {sellthreshold:.4f} DAI/ETH submit a stop limit order.')
    # Enter loop
    while True:
        # Check the status of the submitted ask
        submittedask = client.get_order( orderId=submission["order"]["id"] )
        if submittedask["order"]["status"] == "FILLED":
            # Exit: End the loop and exit.
            logger.info ( f'Order {submittedask["order"]["id"]} was filled at: {submittedask["order"]["price"]:.4f} DAI/ETH.')
            break
        else:
            # Sleep
            # Then check price
            time.sleep(5)
            prices = bestorders( 'WETH-DAI', quotetick )
            topask = Decimal( prices[1] )
            topbid = Decimal( prices[0] )
            asketh = Decimal( prices[2] )
            logger.debug ( f'The highest bid in the orderbook is {topbid-sellthreshold:.4f} DAI above the stop limit {sellthreshold:.4f}.' )

            # Exit loop if the top bid falls below the marker
            if Decimal( prices[0] ) < Decimal( sellthreshold ):
                logger.info ( f'The highest bid in the orderbook [{topbid:.4f} DAI/ETH] just fell below the stop limit [{sellthreshold:.4f} DAI/ETH]')
                # Cancel the previously submitted ask first to avoid any undercapitalization errors.
                logger.info ( "Cancelling order: %s", submittedask["order"]["id"] )
                canceledask = client.cancel_order( hash=submission["order"]["id"] )
                # Display order cancel information
                jsondata = json.dumps( canceledask, sort_keys=True, indent=4, separators=(',', ': ') )
                logger.info ( jsondata )

                # Stop
                try:
                    # Submit order to dYdX
                    logger.debug ( f'Asking {asketh.quantize( quotetick )} DAI/ETH for {quantity:.4f} ETH to stop losses.' )
                    submission = postask( asketh.quantize( quotetick ), quantity )

                except Exception as e:
                    # Throw a critical error notice if anything funky occurs
                    logger.critical("Exception occurred", exc_info=True)

                # Write the submission's response to the logs
                jsondata = json.dumps( submission, sort_keys=True, indent=4, separators=(',', ': ') )
                logger.debug ( f'Order submission:\n{jsondata}' )
                # Report submission information via SMS
                smsalert( f'Bidding {asketh*quantity:.4f} DAI for {quantity:.4f} ETH.' )

                # Loop until the stop is filled
                while True:
                    # Give the stop placed five seconds to fill
                    time.sleep(5)
                    # Get fills
                    lastfill = client.get_my_fills(market=['WETH-DAI'],limit=1)
                    if lastfill["fills"][0]["orderId"] == submission["order"]["id"]:
                        logger.info ( 'Order %s was filled.', submission["order"]["id"])
                        smsalert( f'Stop filled. Asked {bideth:.4f} DAI/ETH and sold {bideth*amount:.4f} DAI for {amount:.4f} ETH.')
                        break

                # Exit loop
                break


    # Sleep
    # Give the blockchain sufficient time
    time.sleep(120)
    # Gave two minutes to write the transaction

    # Withdraw DAI gains if any
    # Check dYdX DAI account balance
    balances = client.eth.get_my_balances()
    newdaibalance = Decimal( balances[consts.MARKET_DAI] / (10**consts.DECIMALS_DAI) )
    logger.info( f'The balance of DAI in the dYdX account is now {newdaibalance:.4f} DAI.' )
    smsalert( f'DAI balance changed by {newdaibalance - daibalance:.4f} DAI because of the last trade.' )
    # Since withdrawals go to the blockchain and need GAS, only withdrawal if gains exceed $2
    if Decimal(newdaibalance) > 2:
        withdrawalhash = client.eth.solo.withdraw_to_zero( market=consts.MARKET_DAI )
        # Display deposit confirmation
        logger.info ( f'Depositing {newdaibalance:10.4f} DAI to the wallet associated with this dYdX account...' )
        receipt = client.eth.get_receipt( withdrawalhash )
        web3out = Web3.toJSON( receipt )
        logger.debug ( web3out )
        logger.info ( 'Done.' )


    logger.info( f'End of liquidity provision.\n\n\n\n' )
