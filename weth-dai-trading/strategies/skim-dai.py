#!/usr/bin/env python3


import sys
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
from creditcalculator import creditavailable
from minimumaskmonitor import monitorminimumask
from maximumbidmonitor import monitormaximumbid
from orderfulfillmentvalidator import validateorderfulfillment


# Define the minimum asset return required and specify trail to increase exposure to the upside.
# A trail of zero results in submitting an ask upon any drop in price after the minimum required return is reached.
# Otherwise, the price must appreciate further beyond the trail. As soon as it does, the minimum asset return starts increasing and never decreases.
# This means that there is unlimited upside to the exit return. However, an exit occurs if the price drops by the trail amount.
#
# Define the price drop/rise before submitting a bid.
#
# Also define a stop (loss) limit ask (just in case the price crashes out of a reasonable trading range).
#
# Finally, define target (mimimum) collateralization ratio and maximum leverage.
# Note: to make a bid without waiting for the prices to fall, set the depreciation trigger to 0.0000001.
logger.info( f'Define execution parameters...' )
exitreturn = 0.0013
pricetrail = 0.0007
exitlosses = 0.027
marketloss = 0.0007
marketgain = 0.0000
minimumroa = ( ( 1 + exitreturn ) * ( 1 + pricetrail ) - 1 )
logger.info ( f'minimumroa = {100*minimumroa:.2f}% minimum increase in the price of ETH before it becomes possible to submit an ask.' )
logger.info ( f'pricetrail = {100*pricetrail:.2f}% minimum decrease in the price of ETH (after attaining the minimum increase in price) before asking starts.' )
logger.info ( f'exitlosses = {100*exitlosses:.2f}% decrease in the price of ETH before asking starts.' )
logger.info ( f'marketgain = {100*marketgain:.2f}% minimum decrease in the price of ETH before bidding starts.' )
logger.info ( f'marketloss = {100*marketloss:.2f}% minimum increase in the price of ETH before bidding starts.' )
# Define the maximim leverage that can be applied going.
# This cannot exceed 5X if going LONG ETH or 4X if going SHORT ETH.
appliedleverage = 3.75
logger.info ( f'appliedleverage = {appliedleverage:.2f}X' )
# dYdX accounts must be overcollateralized at the ratio of 125%.
# Note that positions are liquidated at 115%.
# However, the target collateralization should reflect risk tolerance.
# For example, a cautious trader may feel comfortable using a target of 150%.
# Or the trader may prefer to be overcollateralized at 200% during periods of high volatility.
minimumcollateralization = 1.25
logger.info ( f'minimumcollateralization = {100*minimumcollateralization:.2f}%' )
logger.info( f'Execution parameters defined.\n\n\n\n' )
# Defined execution parameters.


# Define dYdX market tick constant.
markets = client.get_markets()
quotetick = Decimal( markets["markets"]["WETH-DAI"]["minimumTickSize"] )


# Start market maker
while True:
    # Check if this is the first iteration of a complete bid-ask loop.
    # This is required because some bid orders will be canceled by dYdX.
    logger.info( f'Begin providing liquidity for those shorting ETH...' )
    logger.info ( f'Monitor the minimum ask in orderbook channel in a websocket loop...' )
    # Loop until the lowest ask rises above or drops below the market loss or market gain price.
    bideth = asyncio.run( monitorminimumask( '0', marketloss, '0', marketgain ) )

    while True:
        # Set the bid to be a quotetick below the lowest ask.
        bideth = Decimal(bideth) - Decimal(quotetick)

        # Get credit available.
        availablecredit = creditavailable( appliedleverage )

        # Determine most competitive bid price and amount.
        # Make the determination based on the debt remaining and present market values.
        amount = Decimal( availablecredit ) / bideth
        cutoff = consts.SMALL_TRADE_SIZE_WETH / (10 ** consts.DECIMALS_WETH)
        if amount < cutoff:
            logger.debug ('Check account margin or leverage [presently {appliedleverage}X] used.')
            logger.debug ( f'Insufficient collateral. The bid {amount:.4f} is below {cutoff} ETH.' )
            logger.info( f'Unable to provide liquidity for those shorting ETH... Going to sleep for 10 hours.\n\n\n\n' )
            smsalert( f'Invalid bid quantity [{amount:.4f} DAI].' )
            time.sleep(36000)
            continue


        # Bid.
        submission = postbid( bideth.quantize( quotetick ), amount )
        if submission == 'ERROR':
            # Report submission error via SMS.
            smsalert( f'Bid submission error.')
            sys.exit(0)
        else:
            # Report submission information via SMS.
            smsalert( f'Bidding for {amount:.4f} ETH with {bideth*amount:.4f} DAI.' )
            # Check on order fulfillment and loop until the bid is filled.
            orderdetails = client.get_order( orderId=submission["order"]["id"] )
            logger.info ( f'Determining status of:\n{json.dumps( orderdetails, sort_keys=True, indent=4, separators=(",", ": ") )}')
            # If canceled, try again.
            if orderdetails["order"]["status"] == "CANCELED":
                logger.info ( f'Bid order {submission["order"]["id"]} was "CANCELED". Retrying...')
                # There is no need to wait for the trigger again.
                # Simply get the best bid in the orderbook and retry ask.
                bideth = asyncio.run( monitorminimumask( '0', '0', '0', '0' ) )
                continue
            elif orderdetails["order"]["status"] == "FILLED":
                logger.info ( f'Bid order {submission["order"]["id"]} was filled at: {submission["order"]["price"]} DAI/ETH.')
                smsalert( f'Bought {amount:.4f} ETH with {bideth*amount:.4f} DAI at {submission["order"]["price"]} DAI/ETH.')
                # Exit loop.
                break
            else:
                orderstate = asyncio.run( validateorderfulfillment( submission["order"]["id"] ) )
                if orderstate == "CANCELED":
                    logger.info ( f'Bid order {submission["order"]["id"]} was "CANCELED". Retrying...')
                    # There is no need to wait for the trigger again.
                    # Simply get the best bid in the orderbook and retry ask.
                    bideth = asyncio.run( monitorminimumask( '0', '0', '0', '0' ) )
                    continue
                elif orderstate == "FILLED":
                    logger.info ( f'Bid order {submission["order"]["id"]} was filled at: {submission["order"]["price"]} DAI/ETH.')
                    smsalert( f'Bought {amount:.4f} ETH with {bideth*amount:.4f} DAI at {submission["order"]["price"]} DAI/ETH.')
                    # Exit loop.
                    break


    # Loop until the lowest ask exceeds the trigger price or falls below the stop.
    askroa = Decimal(bideth) * ( 1 + Decimal(minimumroa) )
    asketh = asyncio.run( monitormaximumbid( askroa, exitlosses, '0', '0' ) )

    while True:
        # Set the ask to be a quotetick below the highest bid.
        asketh = Decimal(asketh) + Decimal(quotetick)

        # Ask.
        submission = postask( asketh.quantize( quotetick ), amount )
        if submission == 'ERROR':
            # Report submission error via SMS.
            smsalert( f'Ask submission error.')
            sys.exit(0)
        else:
            # Report submission information via SMS.
            smsalert( f'Asking {asketh*amount:.4f} DAI for {amount:.4f} ETH.')
            # Check on order fulfillment and loop until the ask is filled.
            orderdetails = client.get_order( orderId=submission["order"]["id"] )
            logger.info ( f'Determining status of:\n{json.dumps( orderdetails, sort_keys=True, indent=4, separators=(",", ": ") )}')
            # If canceled, try again.
            if orderdetails["order"]["status"] == "CANCELED":
                logger.info ( f'Ask order {submission["order"]["id"]} was "CANCELED". Retrying...')
                # There is no need to wait for the trigger again.
                # Simply get the best bid in the orderbook and retry ask.
                asketh = asyncio.run( monitormaximumbid( '0', '0', '0', '0' ) )
                continue
            elif orderdetails["order"]["status"] == "FILLED":
                askreturn = ( Decimal( submission["order"]["price"] ) - bideth ) * amount
                askequity = amount / appliedleverage
                logger.info ( f'Ask order {submission["order"]["id"]} was filled at: {submission["order"]["price"]} DAI/ETH. Made {askreturn:.2f} DAI.')
                logger.info ( f'Made {100*askreturn/askequity:.2f}% return on {askequity}.')
                smsalert( f'Sold {amount:.4f} ETH for {Decimal(submission["order"]["price"])*amount:.4f} DAI at {submission["order"]["price"]} DAI/ETH. Made {askreturn:.2f} DAI [{100*askreturn/askequity:.2f}% ROE].')
                # Exit program if the stop order was filled.
                if Decimal(asketh) < Decimal(bideth): sys.exit(0)
                # Exit loop.
                break
            else:
                orderstate = asyncio.run( validateorderfulfillment( submission["order"]["id"] ) )
                if orderstate == "CANCELED":
                    logger.info ( f'Ask order {submission["order"]["id"]} was "CANCELED". Retrying...')
                    # There is no need to wait for the trigger again.
                    # Simply get the best bid in the orderbook and retry ask.
                    asketh = asyncio.run( monitormaximumbid( '0', '0', '0', '0' ) )
                    continue
                elif orderstate == "FILLED":
                    askreturn = ( Decimal( submission["order"]["price"] ) - bideth ) * amount
                    askequity = amount / appliedleverage
                    logger.info ( f'Ask order {submission["order"]["id"]} was filled at: {submission["order"]["price"]} DAI/ETH. Made {askreturn:.2f} DAI.')
                    logger.info ( f'Made {100*askreturn/askequity:.2f}% return on {askequity}.')
                    smsalert( f'Sold {amount:.4f} ETH for {Decimal(submission["order"]["price"])*amount:.4f} DAI at {submission["order"]["price"]} DAI/ETH. Made {askreturn:.2f} DAI [{100*askreturn/askequity:.2f}% ROE].')
                    # Exit program if the stop order was filled.
                    if Decimal(asketh) < Decimal(bideth): sys.exit(0)
                    # Exit loop.
                    break


    # Sleep
    blocktime = 180
    # Give the blockchain sufficient time
    # Explain the time afforded the blockchain to write the transaction
    logger.info ( f'Sleeping {blocktime} seconds to let the blockchain do its thang...')
    time.sleep(blocktime)

    # Withdraw DAI gains if any
    # Check dYdX DAI account balance
    balances = client.eth.solo.get_my_balances()
    daifunds = Decimal( balances[consts.MARKET_DAI] / (10**consts.DECIMALS_DAI) )
    logger.info( f'The balance of DAI in the dYdX account is now {daifunds:.4f} DAI.' )
    # Since withdrawals go to the blockchain and need GAS, only withdrawal if gains exceed $2
    if Decimal(daifunds) > 2:
        smsalert( f'The balance of DAI funds is greater than 2 DAI. Withdrawing {daifunds:.4f} DAI.' )
        try:
            withdrawalhash = client.eth.solo.withdraw_to_zero( market=consts.MARKET_DAI )
        except Exception as e:
            # Throw a critical error notice if anything funky occurs
            print ( f'Exception occurred:\n\n{e}\n' )
            sys.exit(0)
        # Display deposit confirmation
        logger.info ( f'Depositing {daifunds:10.4f} DAI to the wallet associated with this dYdX account...' )
        receipt = client.eth.get_receipt( withdrawalhash )
        web3out = Web3.toJSON( receipt )
        strings = str( web3out )
        dataout = json.loads( strings )
        jsonout = json.dumps( dataout, sort_keys=True, indent=4, separators=(',', ': ') )
        logger.debug ( jsonout )


    logger.info( f'End of liquidity provision.\n\n\n\n' )
