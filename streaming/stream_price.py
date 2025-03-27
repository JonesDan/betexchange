import logging
import queue
from threading import Thread, Event
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
from utils import Streaming, bf_login, init_logger
import time
import json
from datetime import datetime
import multiprocessing

logger = init_logger('price_streaming')

redis_client = redis.Redis(host='redis', port=6379)

current_event_id = None
streaming_active = False

pubsub = redis_client.pubsub()
pubsub.subscribe('event_control')
counter = 0

def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def stream_price(event_id):
    # global streaming_active
    streaming_active = True

    logger = init_logger('price_streaming_process')

    logger.info(f"Streaming active:{streaming_active}")

    trading = bf_login(logger)

    # create filters (GB WIN racing)
    market_filter = streaming_market_filter(
        event_ids=[event_id]
    )
    market_data_filter = streaming_market_data_filter(
        fields=["EX_BEST_OFFERS", "EX_MARKET_DEF"], ladder_levels=10
    )

    # create streaming object
    streaming = Streaming(trading, market_filter, market_data_filter)

    # start streaming (runs in new thread and handles any errors)
    streaming.start()
    logger.info(f'*** Stream started for {event_id} ***')

    counter = 0

    try:
        # check for updates in output queue
        while True:
            market_books = streaming.output_queue.get()
            logger.info(f'*** New update for {event_id} ***')
            for market_book in market_books:
                data = market_book.streaming_update
                time = market_book.publish_time
                if 'rc' in data:
                    for data_rc in data['rc']:
                        for b_l in ['batl', 'batb']:
                            if b_l in data_rc:
                                market_id = data['id']
                                selection_id = data_rc['id']
                                summary_odds = {levels[0] : {'price': levels[1], 'size' : levels[2]} for levels in data_rc[b_l]}
                                summary = {market_id : {selection_id: summary_odds}}
                                summary = data_rc | {'selection_id': data_rc['id'] ,'market_id': data['id'], 'update_time': time.strftime('%Y-%m-%dT%H:%M:%S')}
                                redis_client.publish('stream_price', json.dumps(summary))

                    if counter == 0:
                        with open('streaming/price_sample.json', 'w') as json_file:
                            json.dump(data, json_file, indent=4, default=datetime_serializer)
                        counter+=1

    except Exception as e:
        logger.error(f"Error while streaming: {e}")
        pass

    logger.info(f"Streaming stopped for event_id: {event_id}")
    streaming.stop()
    logger.info(f'*** Stream stopped for {event_id} ***')


logger.info(f"Start listening for Event ID")
for message in pubsub.listen():
    if message['type'] == 'message':
        new_event_id = message['data'].decode('utf-8')
        logger.info(f"Received new event_id: {new_event_id}\nCurrent event_id {current_event_id}")

        # Stop the current stream if active
        if current_event_id != new_event_id:
            streaming_active = False
            logger.info(f"Streaming active:{streaming_active}")
            if counter > 0:
                process.terminate()
                process.join()

                # thread.join()
                logger.info(f"Thread finished")

            # Start a new stream
            current_event_id = new_event_id
            if current_event_id != 'Na':
                logger.info(f"Start Streaming thread for {current_event_id}")
                process = multiprocessing.Process(target=stream_price, args=(current_event_id,))
                process.start()

                # thread = Thread(target=stream_price, args=(current_event_id,))
                # thread.start()
                counter+=1
