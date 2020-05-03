#!/usr/bin/env python3

import asyncio

from websocketconnector import checkreturn

askprice = asyncio.run( checkreturn( "bids", "0.0003", '0' ) )
print (askprice)
