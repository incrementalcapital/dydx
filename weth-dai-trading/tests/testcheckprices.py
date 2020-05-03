#!/usr/bin/env python3

import asyncio

from websocketconnector import checkprices

bidprice = asyncio.run( checkprices( "asks", "0.0005", '0.001' ) )
print (bidprice)
