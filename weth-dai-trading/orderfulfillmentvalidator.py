import json
import asyncio
import logging
import websockets
from decimal import Decimal

from credentials import walletaddress

from logger import logger


# Loop through a subscription to the orders channel.
# Continue until the order specified is either "filled" or "canceled".
async def orderfulfillmentstatushandler(
        websocket: websockets.WebSocketClientProtocol,
        subscriptionrequest: dict,
        orderidentification: str
    ) -> None:
    orderstate = ""
    killsocket = False
    async for textoutput in websocket:
        dictionary = json.loads( textoutput )
        # Determine whether messages are updates.
        if "contents" in dictionary:
            # Handle dYdX initial response.
            if "orders" in dictionary["contents"]:
                # Check orders in dYdX initial response for filling of the order id specified.
                for order in dictionary["contents"]["orders"]:
                    if order["id"] == orderidentification:
                        if order["status"] == ("FILLED" or "CANCELED"):
                            orderstate = order["status"]
                            killsocket = True

            # Handle dYdX update response for a filled order.
            if "order" in dictionary["contents"]:
                order = dictionary["contents"]["order"]
                if order["id"] == orderidentification:
                    if order["status"] == ("FILLED" or "CANCELED"):
                        orderstate = order["status"]
                        killsocket = True

            # Exit loop if the order was filled.
            if killsocket:
                logger.debug( f'The order {orderidentification} was filled.' )
                logger.debug( f'Sending request to unsubscribe: {subscriptionrequest["unsubscribe"]}' )
                await channelsubscriptionhandler( websocket, subscriptionrequest["unsubscribe"] )

                logger.debug( f'Closing websocket connection...' )
                await websocket.close(code=1000, reason='order filled.')
                killsocket = False
                return orderstate


async def channelsubscriptionhandler(
        websocket: websockets.WebSocketClientProtocol,
        subscriptionrequest: dict
    ) -> None:
    requestjson = json.dumps( subscriptionrequest )
    await websocket.send( requestjson )


async def constructorderfulfillmentwebsocket(
        orderidentification: str,
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
        return await orderfulfillmentstatushandler( websocket, subscriptionrequest, orderidentification )


async def checkorderfulfillment(
        id: str
    ) ->  None:
    # Define the order identifier.
    ordernumber = id
    # Create a request to subscribe to the orderbook channel.
    requesttext = {
        "subscribe": {
            "type": "subscribe",
            "channel": "orders",
            "id": walletaddress
        },
        "unsubscribe": {
            "type": "unsubscribe",
            "channel": "orders",
            "id": walletaddress
        }
    }
    return await constructorderfulfillmentwebsocket(
            orderidentification = ordernumber,
            subscriptionrequest = requesttext
    )
