import logging
import queue
import threading

import betfairlightweight
import os


# setup logging
logging.basicConfig(level=logging.INFO)  # change to DEBUG to see log all updates

# create trading instance (app key must be activated for streaming)
app_key = os.environ['BF_API_KEY']
username = os.environ['BF_USER']
password = os.environ['BF_PWD']
trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs='/certs')

# login
trading.login()

# create queue
output_queue = queue.Queue()

# create stream listener
listener = betfairlightweight.StreamListener(output_queue=output_queue)

# create stream
stream = trading.streaming.create_stream(listener=listener)

# subscribe
streaming_unique_id = stream.subscribe_to_orders()

# start stream in a new thread (in production would need err handling)
t = threading.Thread(target=stream.start, daemon=True)
t.start()

# check for updates in output queue
while True:
    market_books = output_queue.get()
    # print(market_books)

    for market_book in market_books:
        # print(
        #     market_book,
        #     market_book.streaming_unique_id,  # unique id of stream (returned from subscribe request)
        #     market_book.streaming_update,  # json update received
        #     market_book.market_definition,  # streaming definition, similar to catalogue request
        #     market_book.publish_time,  # betfair publish time of update
        # )
        data = market_book.streaming_update
        print(market_book.publish_time)
        print(market_book.streaming_update)
        print('')
        # order id, matched / unmatched, market_id, closed (time), price, size, selection, status, placed date, matched date, cancelled date, size matched, size remaining, size cancelled
        