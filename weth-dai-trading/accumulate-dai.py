#!/usr/bin/env python3


import json
import time
import asyncio
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
from websocketconnector import checkorderfulfillment
from websocketconnector import pricetriggerorderbookstream


# Specify websocket server (wss protocol assumed)
broadcaster = 'api.dydx.exchange/v1/ws'
# Define the return on assets and price drop (pricetrigger) required for bidding
# Also define a stop limit ask and a stop market ask (just in case the price crashes)
# In addition, define target (mimimum) collateralization ratio and maximum leverage
# Note: to make a bid without waiting for the prices to fall, set the price trigger to 1
logger.info( f'Define execution parameters...' )
pricetrigger = 0.0076
logger.info ( f'pricetrigger = {100*pricetrigger:.2f}% decrease in the price of ETH.' )
# Submit a bid after a 76 basis point drop in the ask price
requiredreturn = 0.013
logger.info ( f'requiredreturn = {100*requiredreturn:.2f}% increase in the price of ETH.' )
# Submit an ask immediately after the bid is filled.
stoplimit = 0.088
logger.info ( f'stoplimit = {100*stoplimit:.2f}% decrease in the price of ETH.' )
# Break out of a loop waiting for the profitable ask to fill if the stop limit is triggered.
appliedleverage = 4.75
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

    # Get best (top) ask, make it an upwardly sliding peg (askpeg), and calculate trigger (marker)
    prices = bestorders( 'WETH-DAI', quotetick )
    topask = Decimal( prices[1] )
    askpeg = topask
    marker = Decimal( askpeg ) * ( 1 - Decimal ( pricetrigger ) )
    logger.info ( f'The lowest ask in the orderbook is {topask:.4f} DAI/ETH' )
    logger.info ( f'To trigger a bid, the lowest ask in the orderbook must fall below {marker:.4f} DAI/ETH' )
    logger.info ( f'Enter a loop to monitor the market...' )
    # Loop until the ask drops below the trigger price.
    asyncio.run( pricetriggerorderbookstream( "bids", marker ) )


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
        logger.debug ( f'Bidding at {bideth.quantize( quotetick )} DAI/ETH for {amount:.4f} ETH.' )
        submission = postbid( bideth.quantize( quotetick ), amount )

    except Exception as e:
        # Throw a critical error notice if anything funky occurs
        logger.critical("Exception occurred", exc_info=True)

    # Write the submission's response to the logs
    jsondata = json.dumps( submission, sort_keys=True, indent=4, separators=(',', ': ') )
    logger.debug ( f'Order submission:\n{jsondata}' )
    # Report submission information via SMS
    smsalert( f'Bidding for {amount:.4f} ETH with {bideth*amount:.4f} DAI.' )


    # Loop until the bid is filled
    asyncio.run( ordersfulfilledstream( submission["order"]["id"] ) )
    logger.info ( f'Order {submission["order"]["id"]} was filled at: {fillprice:.4f} DAI/ETH.')
    smsalert( f'Bought {amount:.4f} ETH with {bideth*amount:.4f} DAI at {fillprice:.4f} DAI/ETH.')


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
    smsalert( f'Asking {askprice*quantity:.4f} DAI for {quantity:.4f} ETH.' )


    # Define stop limit sell order price
    # Right now the dYdX Python client does not support market orders
    # The dYdX stop order is based on the oracle price and it is unwieldy
    sellthreshold = Decimal( bideth ) * ( 1 - Decimal( stoplimit ) )
    logger.info( f'From this point forth, if the submitted ask is not filled and the price drops below {sellthreshold:.4f} DAI/ETH submit a stop limit order.')
    # Enter loop
    while True:
        # Check the status of the submitted ask
        submittedask = client.get_order( orderId=submission["order"]["id"] )
        if submittedask["order"]["status"] == "FILLED":
            fillprice = Decimal( submittedask["order"]["price"] )
            asknumber = submittedask["order"]["id"]
            logger.info ( f'Order {asknumber} was filled at: {fillprice:.4f} DAI/ETH. Made {(fillprice-bideth)*amount:.4f} DAI.')
            smsalert( f'Sold {amount:.4f} ETH for {fillprice*amount:.4f} DAI at {fillprice:.4f} DAI/ETH. Made {(fillprice-bideth)*amount:.4f} DAI.')
            # Ask filled... End loop
            break
        else:
            # Sleep
            # Then check price
            time.sleep(5)
            prices = bestorders( 'WETH-DAI', quotetick )
            topask = Decimal( prices[1] )
            topbid = Decimal( prices[0] )
            asketh = Decimal( prices[2] )
            ethroa = 100 * ( topbid - bideth ) / bideth
            ethroe = ethroa * Decimal(appliedleverage)
            unreal = ( topbid - bideth ) * amount
            logger.debug ( f'Market selling {amount:.4f} ETH now returns {unreal:.4f} DAI [{ethroe:.2f}%] because the highest bid in the orderbook is {topbid:.4f} DAI/ETH. This is {topbid-sellthreshold:.4f} DAI/ETH above the stop limit [{sellthreshold:.4f}].' )

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
                smsalert( f'Asking {asketh*quantity:.4f} DAI for {quantity:.4f} ETH.' )

                # Loop until the stop is filled
                asyncio.run( ordersfulfilledstream( submission["order"]["id"] ) )
                logger.info ( f'Order {submission["order"]["id"]} was filled at: {fillprice:.4f} DAI/ETH. Lost {(bideth-asketh)*amount:.4f} DAI.')
                smsalert( f'Sold {amount:.4f} ETH for {fillprice*amount:.4f} DAI at {fillprice:.4f} DAI/ETH. Lost {(bideth-fillprice)*amount:.4f} DAI.')


    # Sleep
    # Give the blockchain sufficient time
    time.sleep(120)
    # Gave two minutes to write the transaction

    # Withdraw DAI gains if any
    # Check dYdX DAI account balance
    balances = client.eth.solo.get_my_balances()
    daifunds = Decimal( balances[consts.MARKET_DAI] / (10**consts.DECIMALS_DAI) )
    logger.info( f'The balance of DAI in the dYdX account is now {daifunds:.4f} DAI.' )
    # Since withdrawals go to the blockchain and need GAS, only withdrawal if gains exceed $2
    if Decimal(daifunds) > 2:
        smsalert( f'The balance of DAI funds is greater than 2 DAI. Withdrawing {daifunds:.4f} DAI.' )
        withdrawalhash = client.eth.solo.withdraw_to_zero( market=consts.MARKET_DAI )
        # Display deposit confirmation
        logger.info ( f'Depositing {daifunds:10.4f} DAI to the wallet associated with this dYdX account...' )
        receipt = client.eth.get_receipt( withdrawalhash )
        web3out = Web3.toJSON( receipt )
        strings = str( web3out )
        dataout = json.loads( strings )
        jsonout = json.dumps( dataout, sort_keys=True, indent=4, separators=(',', ': ') )
        logger.debug ( jsonout )


    logger.info( f'End of liquidity provision.\n\n\n\n' )
