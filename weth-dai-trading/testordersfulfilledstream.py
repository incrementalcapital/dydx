#!/usr/bin/env python3

import asyncio

from websocketconnector import ordersfulfilledstream

asyncio.run( ordersfulfilledstream( "0xba91f6624a9baba2f74e99e248883a5ab7911b6ab1be534ad25406ff4fb28106" ) )
