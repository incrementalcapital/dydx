#!/usr/bin/env python3

import json
from decimal import *

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from credentials import client


# Get wallet balances
walletbalance = client.eth.get_my_wallet_balance(consts.MARKET_WETH)

# Format balance using DECIMAL information for the asset
balance = Decimal(walletbalance) / (10**consts.DECIMALS_WETH)

print ( f'{balance} ETH' )
