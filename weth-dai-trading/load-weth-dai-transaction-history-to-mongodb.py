#!/usr/bin/env python3


import json
import pymongo

import dydx.constants as consts
import dydx.util as utils

from credentials import client
from dbconnection import dbclient
from dbconnection import tradingaccount


# Get trades created by my account
wethdaitrades = client.get_my_trades(
    market=['WETH-DAI'],
    limit=None,  # optional
    startingBefore=None  # optional
)

db = dbclient[tradingaccount]
collection = db["wethdaitransactionhistory"]
for trade in wethdaitrades["trades"]:
    transactionhistory = collection.insert_one(trade)
