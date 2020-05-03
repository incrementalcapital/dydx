#!/usr/bin/env python3

from decimal import Decimal

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from credentials import client


# Get wallet balances
ethwalletbalance = client.eth.get_my_wallet_balance(consts.MARKET_WETH)
usdwalletbalance = client.eth.get_my_wallet_balance(consts.MARKET_USDC)
daiwalletbalance = client.eth.get_my_wallet_balance(consts.MARKET_DAI)

# Format wallet balances using DECIMAL information for the asset
formattedethwalletbalance = Decimal(ethwalletbalance) / (10**consts.DECIMALS_WETH)
formattedusdwalletbalance = Decimal(usdwalletbalance) / (10**consts.DECIMALS_USDC)
formatteddaiwalletbalance = Decimal(daiwalletbalance) / (10**consts.DECIMALS_DAI)

# Get dYdX account balances
accountbalances = client.eth.solo.get_my_balances()

# Disaggregate asset account balances
ethaccountbalance = Decimal(accountbalances[consts.MARKET_WETH] / (10**consts.DECIMALS_WETH))
usdaccountbalance = Decimal(accountbalances[consts.MARKET_USDC] / (10**consts.DECIMALS_USDC))
daiaccountbalance = Decimal(accountbalances[consts.MARKET_DAI] / (10**consts.DECIMALS_DAI))

# Display dYdX account balance information
print (f'{ethaccountbalance:28.4f} ETH [Wallet Balance: {formattedethwalletbalance:.8f}]')
print (f'{usdaccountbalance:28.4f} USD [Wallet Balance: {formattedusdwalletbalance:.8f}]')
print (f'{daiaccountbalance:28.4f} DAI [Wallet Balance: {formatteddaiwalletbalance:.8f}]')
