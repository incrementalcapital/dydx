#!/usr/bin/env python3

from decimal import Decimal

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from credentials import client


# Get dYdX account balances
balances = client.eth.solo.get_my_balances()

# Disaggregate asset balances
ethbalance = Decimal(balances[consts.MARKET_WETH] / (10**consts.DECIMALS_WETH))
usdbalance = Decimal(balances[consts.MARKET_USDC] / (10**consts.DECIMALS_USDC))
daibalance = Decimal(balances[consts.MARKET_DAI] / (10**consts.DECIMALS_DAI))

# Display dYdX account balance information
print (f'{ethbalance:28.4f} ETH')
print (f'{usdbalance:28.4f} USD')
print (f'{daibalance:28.4f} DAI')
