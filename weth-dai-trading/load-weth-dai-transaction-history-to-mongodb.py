#!/usr/bin/env python3


import dns
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

# Create a database
# Use the "trading account" identifier provided
db = dbclient[tradingaccount]
# [ALTERNATIVE SYNTAX] : db = dbclient.<tradingaccount>

# Create a collection
transactioncollection = db["wethdaitransactionhistory"]
# [ALTERNATIVE SYNTAX] : transactioncollection = db.wethdaitransactionhistory

# Insert documents into the collection
# This is done one-at-a-time below
for trade in wethdaitrades["trades"]:
    transactionhistory = transactioncollection.insert_one(trade)
