#!/usr/bin/env python3

from dydx.client import Client
import dydx.constants as consts
import dydx.util as utils

from credentials import client


# Get dYdX account collateralization
collateralization = client.eth.solo.get_my_collateralization()

print ( f'{collateralization*100:28.4f}%' )
