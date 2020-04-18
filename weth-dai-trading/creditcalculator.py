#!/usr/bin/env python3


from decimal import Decimal

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from logger import logger
from credentials import client


# dYdX allows margin trades
# Essentially, it offers a credit facility
# This module determines credit available
# Calculations are based on the value of the dYdX account
def creditavailable( leverage ):
    # Get (set) dYdX markets and define market constants
    minimumcollateralization = 1.25

    # Get dYdX index price for DAI returned in US dollar terms
    # dYdX uses price oracles for DAI
    oracleprice = client.eth.solo.get_oracle_price( consts.MARKET_DAI )
    normalprice = Decimal(oracleprice) * 10**( consts.DECIMALS_DAI )
    daiusdprice = Decimal(normalprice)
    logger.debug( f'The oracles says 1 DAI is: {daiusdprice:10.4f} US dollars')


    # Get dYdX account balances
    balances = client.eth.solo.get_my_balances()
    # Determine overcollateralized collateral (USDC asset balance in DAI terms)
    # And DAI balance to determine the maximum amount of DAI borrowable
    # Do not use the Oracle Price for ETH because it is inaccurate for present debt calculations
    ethbalance = Decimal( balances[ consts.MARKET_WETH ] / ( 10**consts.DECIMALS_WETH ) ) * Decimal(daiusdprice)
    usdbalance = Decimal( balances[ consts.MARKET_USDC ] / ( 10**consts.DECIMALS_USDC ) ) / Decimal(daiusdprice)
    daibalance = Decimal( balances[ consts.MARKET_DAI ] / ( 10**consts.DECIMALS_DAI ) )
    # Determine the DAI value of the dYdX account and the margin that affords
    # Calculate the maximum additional debt allowed (in DAI terms)
    dydxaccount = Decimal(ethbalance) + Decimal(usdbalance) + Decimal(daibalance)
    totalmargin = Decimal(dydxaccount) / Decimal(minimumcollateralization)
    creditlimit = Decimal(totalmargin) * Decimal(leverage)
    # Define pertinent DAI liabilities
    if Decimal( daibalance ) < 0:
        liabilities = abs( daibalance )
    else:
        liabilities = 0
    logger.debug( f'This dYdX account has DAI liabilities of: {liabilities:10.4f} DAI')
    # Determine the available debt accessible to the dYdX account
    availablecredit = Decimal(creditlimit) - Decimal(liabilities)
    # Note: going long on ETH with DAI means having to remove the existing DAI liabilities in the calculation
    logger.debug ( f'This dYdX account has a balance of {dydxaccount:10.4f} [in DAI terms].')
    logger.debug ( f'Presently has {ethbalance:10.4f} ETH [a negative sign indicates debt].')
    logger.debug ( f'Presently has {usdbalance:10.4f} USD [a negative sign indicates debt].')
    logger.debug ( f'Presently has {daibalance:10.4f} DAI [a negative sign indicates debt].')
    logger.debug ( f'dYdX allows {100/minimumcollateralization:5.2f}% for trades on margin.')
    logger.debug ( f'The maximum possible liability allowed is now {creditlimit:10.4f} DAI.')
    logger.debug ( f'This is thanks to {leverage:5.2f}X leverage on {totalmargin:5.2f} DAI.')
    logger.debug ( f'Credit available to this dYdX account is: {availablecredit:10.4f} DAI.')

    return availablecredit
