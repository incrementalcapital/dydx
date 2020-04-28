import json
import asyncio
import logging
import websockets
from decimal import Decimal

from logger import logger


async def websocketaskpricehandler(
        websocket: websockets.WebSocketClientProtocol,
        subscriptionrequest: dict,
        orderpricelevelexit: str
    ) -> None:
    killsocket = False
    marketdata = {}
    minimumask = float("inf")
    async for textoutput in websocket:
        dictionary = json.loads( textoutput )
        # Determine whether messages are updates.
        if "contents" in dictionary:
            # Handle dYdX initial response.
            if "updates" not in dictionary["contents"]:
                # Get the best ask price from dYdX initial response.
                minimumask = dictionary["contents"]["asks"][0]["price"]
                logger.debug( f'initial information received... the lowest ask in the orderbook is: {Decimal(minimumask):.2f} DAI/ETH [Message ID: {dictionary["message_id"]}].' )
                # Load orderbook into updateable market data dictionary.
                marketdata = dictionary["contents"]["asks"]
            else:
                for updatedata in dictionary["contents"]["updates"]:

                    # Update best ask prices.
                    if updatedata["side"] == "SELL":
                        if updatedata["type"] == "NEW":
                            orderentry = {
                                "id": updatedata["id"],
                                "uuid": "",
                                "amount": updatedata["amount"],
                                "price": updatedata["price"],
                            }
                            marketdata.append(orderentry)

                        if updatedata["type"] == "REMOVED":
                            marketdata = list(
                                filter(lambda i: i["id"] !=
                                    updatedata["id"],
                                    marketdata
                                    )
                            )

                        if updatedata["type"] == "UPDATED":
                            if "price" in updatedata:
                                ordernumber = index(updatedata["id"])
                                marketdata["price"][ordernumber] = updatedata["price"]

                    # Rank asks and determine the lowest ask in the orderbook.
                    askranking = [Decimal(order["price"]) for order in marketdata]
                    minimumask = min(askranking)

                    # Display price updates.
                    logger.debug( f'updated information received... the lowest ask in the orderbook is: {Decimal(minimumask):.2f} DAI/ETH [Message ID: {dictionary["message_id"]}].' )

                    # Exit if the maximum ask drops below the exit trigger.
                    if minimumask > Decimal(orderpricelevelexit):
                        if not killsocket:
                            logger.debug( f'The lowest ask in the orderbook just exceed {orderpricelevelexit} DAI/ETH.' )
                            logger.debug( f'Sending request to unsubscribe: {subscriptionrequest["unsubscribe"]}' )
                            await channelsubscriptionhandler( websocket, subscriptionrequest["unsubscribe"] )

                            logger.debug( f'Closing websocket connection...' )
                            await websocket.close(code=1000, reason='exit trigger reached.')
                            killsocket = True


async def websocketbidpricehandler(
        websocket: websockets.WebSocketClientProtocol,
        subscriptionrequest: dict,
        orderpricelevelexit: str
    ) -> None:
    killsocket = False
    marketdata = {}
    maximumbid = float("-inf")
    async for textoutput in websocket:
        dictionary = json.loads( textoutput )
        # Determine whether messages are updates.
        if "contents" in dictionary:
            # Handle dYdX initial response.
            if "updates" not in dictionary["contents"]:
                # Get the best bid price from dYdX initial response.
                maximumbid = dictionary["contents"]["bids"][0]["price"]
                logger.debug( f'initial information received... the highest bid in the orderbook is: {Decimal(maximumbid):.2f} DAI/ETH [Message ID: {dictionary["message_id"]}].' )
                # Load orderbook into updateable market data dictionary.
                marketdata = dictionary["contents"]["bids"]
            else:
                for updatedata in dictionary["contents"]["updates"]:

                    # Update best bid prices.
                    if updatedata["side"] == "BUY":
                        if updatedata["type"] == "NEW":
                            orderentry = {
                                "id": updatedata["id"],
                                "uuid": "",
                                "amount": updatedata["amount"],
                                "price": updatedata["price"],
                            }
                            marketdata.append(orderentry)

                        if updatedata["type"] == "REMOVED":
                            marketdata = list(
                                filter(lambda i: i["id"] !=
                                    updatedata["id"],
                                    marketdata
                                    )
                            )

                        if updatedata["type"] == "UPDATED":
                            if "price" in updatedata:
                                ordernumber = index(updatedata["id"])
                                marketdata["price"][ordernumber] = updatedata["price"]

                    # Rank bids and determine the highest bid in the orderbook.
                    bidranking = [Decimal(order["price"]) for order in marketdata]
                    maximumbid = max(bidranking)

                    # Display price updates.
                    logger.debug( f'updated information received... the highest bid in the orderbook is: {Decimal(maximumbid):.2f} DAI/ETH [Message ID: {dictionary["message_id"]}].' )

                    # Exit if the maximum bid drops below the exit trigger.
                    if maximumbid < Decimal(orderpricelevelexit):
                        if not killsocket:
                            logger.debug( f'The highest bid in the orderbook just fell below {orderpricelevelexit} DAI/ETH.' )
                            logger.debug( f'Sending request to unsubscribe: {subscriptionrequest["unsubscribe"]}' )
                            await channelsubscriptionhandler( websocket, subscriptionrequest["unsubscribe"] )

                            logger.debug( f'Closing websocket connection...' )
                            await websocket.close(code=1000, reason='exit trigger reached.')
                            killsocket = True


async def channelsubscriptionhandler(
        websocket: websockets.WebSocketClientProtocol,
        subscriptionrequest: dict
    ) -> None:
    requestjson = json.dumps( subscriptionrequest )
    await websocket.send( requestjson )


async def websocketchannelsubscription(
        orderexecutionstate: str,
        orderpricelevelexit: str,
        subscriptionrequest: dict
    ) -> None:
    # Initialize channel requested toggle.
    # Define the URL of the websocket server.
    channelsubscription = False
    url = f'wss://api.dydx.exchange/v1/ws'
    logger.debug( f'Using websockets library to connect to {url}...' )

    # Connect websocket.
    async with websockets.connect( url ) as websocket:
        if not channelsubscription:
            logger.debug( f'Sending the following channel subscription request to {url}: {subscriptionrequest["subscribe"]}' )
            await channelsubscriptionhandler( websocket, subscriptionrequest["subscribe"] )
            channelsubscription == True
        if orderexecutionstate == "bids":
            await websocketbidpricehandler( websocket, subscriptionrequest, orderpricelevelexit )
        if orderexecutionstate == "asks":
            await websocketaskpricehandler( websocket, subscriptionrequest, orderpricelevelexit )


async def monitorwethdaiorderbookchannel(
        orderexecutionstate: str,
        orderpricelevelexit: str,
    ) ->  None:
    # Define the order type [BUY/SELL].
    orderstatus = orderexecutionstate
    # Define the price that triggers the loop exit.
    exittrigger = orderpricelevelexit
    # Create a request to subscribe to the orderbook channel.
    requesttext = {
        "subscribe": {
            "type": "subscribe",
            "channel": "orderbook",
            "id": "WETH-DAI"
        },
        "unsubscribe": {
            "type": "unsubscribe",
            "channel": "orderbook",
            "id": "WETH-DAI"
        }
    }
    await websocketchannelsubscription(
            orderexecutionstate = orderstatus,
            orderpricelevelexit = exittrigger,
            subscriptionrequest = requesttext
    )
