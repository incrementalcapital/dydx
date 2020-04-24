import json
import asyncio
import logging
import websockets


logging.basicConfig(level=logging.INFO)


async def websocketmessagehandler( websocket: websockets.WebSocketClientProtocol ) -> None:
    async for textoutput in websocket:
        dictionary = json.loads( textoutput )
        parsedjson = json.dumps( dictionary, sort_keys=True, indent=4, separators=(',', ': ') )
        logmessage( parsedjson )


async def connectionrequesthandler( websocket: websockets.WebSocketClientProtocol, subscriptionrequest: dict ) -> None:
    await websocket.send( subscriptionrequest )


async def receivewebsocketchanneldata( hostname: str, subscriptionrequest: dict, channelsubscribed: bool ) -> None:
    websocket_resource_url = f'wss://{hostname}'
    async with websockets.connect( websocket_resource_url ) as websocket:
        if not channelsubscribed:
            await connectionrequesthandler( websocket, subscriptionrequest )
            channelsubscribed == True
        await websocketmessagehandler( websocket )


def logmessage(message: str) -> None:
    logging.info(f'\n{message}')


if __name__ == '__main__':

    # Specify websocket server (wss protocl assumed)
    websocketserver = 'api.dydx.exchange/v1/ws'
    # Create a request to subscribe to the orderbook channel.
    requesttext = {
        "type": "subscribe",
        "channel": "orderbook",
        "id": "WETH-DAI"
    }
    requestjson = json.dumps( requesttext )
    # Initialize channel requested toggle
    channelrequested = False

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        receivewebsocketchanneldata(
            hostname = websocketserver,
            subscriptionrequest = requestjson,
            channelsubscribed = channelrequested
        )
    )
    loop.run_forever()
