import json
import asyncio
import logging
import websockets
from decimal import Decimal
from sys import exit

from credentials import walletaddress

from logger import logger


async def maximumbidmessagehandler(
        websocket: websockets.WebSocketClientProtocol,
        subscriptionrequest: dict,
        initialminimumprice: str,
        percentdepreciation: str,
        initialmaximumprice: str,
        percentappreciation: str
    ) -> None:

    marketdata = {}
    maximumbid = ""
    killsocket = False
    upperlimit = float("inf")
    lowerlimit = float("-inf")

    async for textoutput in websocket:
        dictionary = json.loads( textoutput )

        # Determine whether messages are updates.
        if "contents" in dictionary:

            # Handle dYdX initial response.
            if "updates" not in dictionary["contents"]:

                # Get the best bid price from dYdX initial response.
                maximumbid = dictionary["contents"]["bids"][0]["price"]

                # Display price information.
                logger.debug( f'initial information received... [lower price bound / upper price bound : {lowerlimit:.2f}/{upperlimit:.2f} DAI/ETH] the highest bid in the orderbook is: {Decimal(maximumbid):.2f} DAI/ETH [Message ID: {dictionary["message_id"]}].' )

                # Load orderbook into updateable market data dictionary.
                marketdata = dictionary["contents"]["bids"]

            # Handle dYdX update response.
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

                    # Rank bids and determine the highest bid in the orderbook from dYdX update response.
                    bidranking = [Decimal(order["price"]) for order in marketdata]
                    maximumbid = max(bidranking)

                    # Display price updates.
                    logger.debug( f'updated information received... [lower price bound / upper price bound : {lowerlimit:.2f}/{upperlimit:.2f} DAI/ETH] the highest bid in the orderbook is: {Decimal(maximumbid):.2f} DAI/ETH [Message ID: {dictionary["message_id"]}].' )

                    # Depreciation Logic
                    #
                    # [This logic handles INCREASES in the maximum bid price as long as it does not fall below the depreciation trigger.]
                    #
                    # Use the following logic if there is an initial minimum price.
                    # Set the lower exit price to the depreciation trigger price.
                    # This is calculated once. It is determined in the first update message.
                    # The maximum bid must rise above this initial minimum price.
                    # Exit if the maximum bid drops below the upwardly sliding lower limit.
                    if Decimal(initialminimumprice):
                        if lowerlimit == float("-inf"): lowerlimit = Decimal(maximumbid) * ( 1 - Decimal(percentdepreciation) )
                        if Decimal(maximumbid) * ( 1 - Decimal(percentdepreciation) ) > Decimal(initialminimumprice):
                            if Decimal(maximumbid) * ( 1 - Decimal(percentdepreciation) ) < lowerlimit:
                                logger.debug( f'The highest bid [{Decimal(maximumbid):.2f} DAI/ETH] in the orderbook just dropped below a {Decimal(percentdepreciation)*100:.2f}% margin over the lower price bound [{lowerlimit:.2f} DAI/ETH].' )
                                killsocket = True
                            else:
                                lowerlimit = Decimal(maximumbid) * ( 1 - Decimal(percentdepreciation) )
                    # Appreciation Logic
                    #
                    # [This logic handles DECREASES in the maximum bid price as long as it does not rise below the appreciation trigger.]
                    #
                    # Use the following logic if there is an initial maximum price.
                    # Set the upper exit price to the appreciation trigger price.
                    # This is calculated once. It is determined in the first update message.
                    # The maximum bid must fall below above this initial maximum price.
                    # Exit if the maximum bid rises above the downwardly sliding upper limit.
                    elif Decimal(initialmaximumprice):
                        if upperlimit == float("inf"): upperlimit = Decimal(maximumbid) * ( 1 + Decimal(percentappreciation) )
                        if Decimal(maximumbid) * ( 1 + Decimal(percentappreciation) ) < Decimal(initialmaximumprice):
                            if Decimal(maximumbid) * ( 1 + Decimal(percentappreciation) ) > upperlimit:
                                logger.debug( f'The highest bid [{Decimal(maximumbid):.2f} DAI/ETH] in the orderbook just exceeded a {percentappreciation*100:.2f}% margin below the upper price bound [{upperlimit:.2f} DAI/ETH].' )
                                killsocket = True
                            else:
                                upperlimit = Decimal(maximumbid) * ( 1 + Decimal(percentappreciation) )
                    else:
                        # If the desired percentage depreciation is set to zero (FALSE), let the lower exit price remain at negative infinity.
                        # Otherwise (percentdepreciation is TRUE), use any increase in maximum bid to determine a new lower price exit.
                        # The lower exit price never decreases if the bid price decreases (assuming percentdepreciation is positive).
                        # Specifically: Increase the lower exit price proportional to the bid price increase.
                        #
                        # Note the following use case:
                        # - Set percent depreciation very near to zero (but positive) to trigger an exit for any depreciation in maximum bid price.
                        if Decimal(percentdepreciation):
                            if Decimal(maximumbid) * ( 1 - Decimal(percentdepreciation) ) > lowerlimit:
                                lowerlimit = Decimal(maximumbid) * ( 1 - Decimal(percentdepreciation) )
                            elif Decimal(maximumbid) < lowerlimit:
                                logger.debug( f'The highest bid [{Decimal(maximumbid):.2f} DAI/ETH] in the orderbook just dropped below the lower price bound [{lowerlimit:.2f} DAI/ETH].' )
                                killsocket = True
                        # If the desired percentage appreciation is set to zero (FALSE), let the upper exit price remain at positive infinity.
                        # Otherwise (percentappreciation is TRUE), use any decrease in maximum bid to determine a new upper price exit.
                        # The upper exit price never increases if the bid price increases (assuming percentappreciation is positive).
                        # Specifically: Decrease the upper exit price proportional to the bid price decrease.
                        #
                        # Note the following use case:
                        # - Set percent appreciation very near to zero (but positive) to trigger an exit for any appreciation in maximum bid price.
                        if Decimal(percentappreciation):
                            if Decimal(maximumbid) * ( 1 + Decimal(percentappreciation) ) < upperlimit:
                                upperlimit = Decimal(maximumbid) * ( 1 + Decimal(percentappreciation) )
                            elif Decimal(maximumbid) > upperlimit:
                                logger.debug( f'The highest bid [{Decimal(maximumbid):.2f} DAI/ETH] in the orderbook just exceeded the upper price bound [{upperlimit:.2f} DAI/ETH].' )
                                killsocket = True
                        # Exit loop if there are no appreciation and depreciation triggers.
                        if not Decimal(percentdepreciation) and not Decimal(percentappreciation): killsocket = True

                    # Run the killsocket routine just once.
                    if killsocket:

                        logger.debug( f'Sending request to unsubscribe: {subscriptionrequest["unsubscribe"]}' )
                        await channelsubscriptionhandler( websocket, subscriptionrequest["unsubscribe"] )

                        logger.debug( f'Closing websocket connection...' )
                        await websocket.close(code=1000, reason='exit trigger reached.')

                        killsocket = False
                        return maximumbid


async def channelsubscriptionhandler(
        websocket: websockets.WebSocketClientProtocol,
        subscriptionrequest: dict
    ) -> None:
    requestjson = json.dumps( subscriptionrequest )
    await websocket.send( requestjson )


async def monitormaximumbidwebsocket(
        initialminimumprice: str,
        percentdepreciation: str,
        initialmaximumprice: str,
        percentappreciation: str,
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
        return await maximumbidmessagehandler(
            websocket,
            subscriptionrequest,
            initialminimumprice,
            percentdepreciation,
            initialmaximumprice,
            percentappreciation
        )


async def monitormaximumbid(
        initialminimumprice: str,
        depreciationtrigger: str,
        initialmaximumprice: str,
        appreciationtrigger: str
    ) ->  None:
    # Create a request to subscribe to the orderbook channel.
    subscriptionstrings = {
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
    # Display configuration parameters.
    logger.debug( f'configure "initialminimumprice" to: {initialminimumprice} DAI/ETH.' )
    logger.debug( f'configure "initialmaximumprice" to: {initialmaximumprice} DAI/ETH.' )
    logger.debug( f'configure "depreciationtrigger" to: {Decimal(depreciationtrigger)*100:.2f} %.' )
    logger.debug( f'configure "appreciationtrigger" to: {Decimal(appreciationtrigger)*100:.2f} %.' )

    return await monitormaximumbidwebsocket(
        initialminimumprice,
        depreciationtrigger,
        initialmaximumprice,
        appreciationtrigger,
        subscriptionstrings
    )


if __name__ == "__main__":
    initialminimumprice = '206.13'
    depreciationtrigger = '0.007'
    initialmaximumprice = '0'
    appreciationtrigger = '0.0013'
    try:
        asyncio.run( monitormaximumbid( initialminimumprice, depreciationtrigger, initialmaximumprice, appreciationtrigger ) )
    except KeyboardInterrupt:
        logger.debug( f'exception: keyboard interuption.' )
    except Exception as e:
        logger.debug( f'exception: {e}.' )
    logger.debug( f'exiting...' )
    exit(0)
