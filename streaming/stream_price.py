import logging
import queue
from threading import Thread
from tenacity import retry, wait_exponential

import betfairlightweight
from betfairlightweight import StreamListener
from betfairlightweight import BetfairError
from betfairlightweight.filters import (
    streaming_market_filter,
    streaming_market_data_filter,
)
import os
import redis
from utils import Streaming
import time
import json

"""
Streaming example to handle timeouts or connection errors, 
with reconnect.

Code uses 'tenacity' library for retrying.

Streaming class inherits threading module to simplify start/
stop.
"""

# setup logging
logging.basicConfig(level=logging.INFO)  # change to DEBUG to see log all updates
logger = logging.getLogger(__name__)

redis_client = redis.Redis(host='redis', port=6379)

current_event_id = None
streaming_active = False

def stream_price(event_id):
    global streaming_active
    streaming_active = True
    logger.info(f"streaming_active = {streaming_active}")

    # create trading instance (app key must be activated for streaming)
    app_key = os.environ['BF_API_KEY']
    username = os.environ['BF_USER']
    password = os.environ['BF_PWD']
    trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs='/certs')

    # login
    trading.login()

    # create filters (GB WIN racing)
    market_filter = streaming_market_filter(
        event_ids=[event_id]
    )
    market_data_filter = streaming_market_data_filter(
        fields=["EX_BEST_OFFERS", "EX_MARKET_DEF"], ladder_levels=3
    )               

    # create streaming object
    streaming = Streaming(trading, market_filter, market_data_filter)

    # start streaming (runs in new thread and handles any errors)
    streaming.start()
    logger.info(f'*** start stream ***')

    try:
        # check for updates in output queue
        while streaming_active:
            market_books = streaming.output_queue.get()

            for market_book in market_books:
                # print(
                #     # market_book.streaming_unique_id,  # unique id of stream (returned from subscribe request)
                #     market_book.streaming_update,  # json update received
                #     # market_book.market_definition,  # streaming definition, similar to catalogue request
                #     # market_book.publish_time,  # betfair publish time of update
                # )
                data = market_book.streaming_update
                time = market_book.publish_time
                if 'rc' in data:
                    for d in data['rc']:
                        if 'batl' in d:
                            for d1 in d['batl']:
                                summary = {'id':str(data['id']) + '-' + str(d['id']) + '-' + 'LAY','market_id':data['id'],'selection_id':d['id'] ,'level':d1[0], 'price':d1[1] ,'size':d1[2],'b_l':'LAY', 'update_time':time.strftime('%Y-%m-%dT%H:%M:%S')}
                                print(summary)
                                redis_client.publish('stream_price', json.dumps(summary))

                        if 'batb' in d:
                            for d2 in d['batb']:
                                summary = {'id':str(data['id']) + '-' + str(d['id']) + '-' + 'BACK','market_id':data['id'],'selection_id':d['id'] ,'level':d2[0], 'price':d2[1] ,'size':d2[2],'b_l':'BACK', 'update_time':time.strftime('%Y-%m-%dT%H:%M:%S')}
                                print(summary)
                                redis_client.publish('stream_price', json.dumps(summary))
    except Exception as e:
        print(f"Error while streaming: {e}")
        pass

    print(f"Streaming stopped for event_id: {event_id}")
    streaming.stop()

def listen_for_event_id():
    """Listen to Redis for new event_id and manage the stream."""
    global current_event_id, streaming_active
    pubsub = redis_client.pubsub()
    pubsub.subscribe('event_control')

    for message in pubsub.listen():
        if message['type'] == 'message':
            new_event_id = message['data'].decode('utf-8')
            logger.info(f"Received new event_id: {new_event_id}")

            # Stop the current stream if active
            if streaming_active and current_event_id != new_event_id:
                streaming_active = False
                logger.info(f"streaming_active = {streaming_active}")
                time.sleep(1)  # Ensure the current stream stops cleanly

            # Start a new stream
            current_event_id = new_event_id
            Thread(target=stream_price, args=(current_event_id,)).start()

if __name__ == "__main__":
    # Start listening for event_id updates
    Thread(target=listen_for_event_id).start()