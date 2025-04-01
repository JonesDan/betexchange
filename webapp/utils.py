
from flask_sse import sse
import json
import os
import betfairlightweight
import logging
from datetime import datetime, timedelta
import shelve
import pandas as pd
import numpy as np
from betfairlightweight import filters
from betfairlightweight.filters import (
    streaming_market_filter,
    streaming_market_data_filter,
)

import queue
import threading
from tenacity import retry, wait_exponential
from betfairlightweight import StreamListener
from betfairlightweight import BetfairError
from cryptography.fernet import Fernet
import time
import redis


def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def init_logger(filename):
    # Logging
    filepath = f'logs/{filename}.log'
    logging.basicConfig(level=logging.INFO
                        , filename=filepath
                        , format='%(asctime)s - %(levelname)s - %(message)s'
                        )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create file handler
    file_handler = logging.FileHandler(filepath)
    file_handler.setLevel(logging.DEBUG)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def bf_login(username, password):
    # create trading instance (app key must be activated for streaming)
    app_key = os.environ['BF_API_KEY']
    # username = os.environ['BF_USER']
    # password = os.environ['BF_PWD']
    trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs='/certs', lightweight=True)

    # Log in to Betfair API
    trading.login()

    return trading



def prices_listener(app, redis_client):
    logger = init_logger('prices_listener')
    logger.info('Begin Listening to Prices stream')
    with app.app_context():
        pubsub = redis_client.pubsub()
        pubsub.subscribe('stream_price')
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    update_data = message['data'].decode('utf-8')
                    logger.info(f'Received New Message. Message:{update_data}')
                    update_data = json.loads(update_data)
                    market_id = update_data['market_id']
                    selection_id = update_data['id']
                    update_time = update_data['update_time']
                    for b_l in ['batl', 'batb']:
                        if b_l in update_data:
                            for l in update_data[b_l]:
                                id = f"{market_id}-{selection_id}-{b_l}-{l[0]}"
                                price = l[1]
                                size = l[2]
                                data = {'price': price, 'size': size, 'level': l[0], 'market_id': market_id, 'selection_id': selection_id, 'b_l': b_l, 'update_time': update_time}
                                with shelve.open('shelve/price_cache.db') as cache:
                                    cache[id] = data
                                sse.publish(data, type='update', channel='prices')
        except Exception as e:
            logger.error(f"Error Listening: {e}")
            pass


def orders_listener(app, redis_client):
    logger = init_logger('orders_listener')
    logger.info('Begin Listening to Orders stream')
    with app.app_context():
        pubsub = redis_client.pubsub()
        pubsub.subscribe('Orders')
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    update_data = message['data'].decode('utf-8')
                    logger.info(f'Received New Orders Message. Message:{update_data}')
                    update_data = json.loads(update_data)

                    with shelve.open('shelve/market_catalogue.db') as cache:
                        market_catalogue = dict(cache['market_catalogue'])

                    market_name = market_catalogue[update_data['market_id']][0]['market_name']
                    selection_name = update_data['selection_id']
                    for selection in market_catalogue[update_data['market_id']]:
                        if update_data['selection_id'] == selection['selection_id']:
                            selection_name = selection['selection_name']

                    data = {'market_name': market_name,
                            'selection_name':  selection_name,
                            'order_id':  update_data['id'],
                            'update_time': update_data['update_time'],
                            'b_l':update_data['side'], 
                            'price': update_data['p'], 
                            'size': update_data['s'],
                            'matched': update_data['sm'],
                            'remaining': update_data['sr'],
                            'lapsed': update_data['sl'],
                            'cancelled': update_data['sc'],
                            'voided': update_data['sv'],
                            'id': update_data['id']
                            }
                    
                    logger.info(data)

                    sse.publish(data, type='update', channel='orders')  

                    with shelve.open("shelve/orders.db", writeback=True) as db:
                        db.setdefault("my_list", []).append(data)
                        summary = db['my_list']
                    
                    df = pd.DataFrame(summary)

                    df['price'] = df['price'].astype('float')
                    df['stake'] = df['size'].astype('float')
                    df['bk_price'] = np.where(df['b_l'] == 'B', df['price'], 0)
                    df['bk_stake'] = np.where(df['b_l'] == 'B', df['stake'], 0)
                    df['bk_profit'] = np.where(df['b_l'] == 'B', df['price'] * df['stake'], 0)
                    df['lay_stake'] = np.where(df['b_l'] == 'L', df['stake'], 0)
                    df['lay_liability'] = np.where(df['b_l'] == 'L', (df['price']-1) * df['stake'], 0)
                    df['lay_payout'] = np.where(df['b_l'] == 'L', df['stake'], 0)

                    df_summary = df[['market_name','selection_name','bk_price','bk_stake','bk_profit','lay_stake','lay_liability','lay_payout']].groupby(['market_name','selection_name']).sum().reset_index()

                    df_summary[['bk_price','bk_stake','bk_profit','lay_stake','lay_liability','lay_payout']] = df_summary[['bk_price','bk_stake','bk_profit','lay_stake','lay_liability','lay_payout']].applymap(lambda x: f"{x:.2f}")

                    result_list = df_summary.to_dict(orient='records')
                    logger.info(result_list)                    

                    sse.publish(result_list, type='update', channel='orders_agg')  
                    
        except Exception as e:
            logger.error(f"Error Listening: {e}")
            pass


def clear_shelve():
    for filename in ['shelve/market_catalogue.db', 'shelve/price_cache.db' ,'shelve/orders.db']:
        with shelve.open(filename) as db:
            db.clear()
            

def place_order(trading, selection_id, b_l, market_id, size, price, sizeMin, result_queue):
    # placing an order
    instructions = []
    order_response = []

    limit_order = filters.limit_order(size=size, price=price, persistence_type="LAPSE", time_in_force="FILL_OR_KILL", min_fill_size=sizeMin)
    instruction = filters.place_instruction(
        order_type="LIMIT",
        selection_id=selection_id,
        side=b_l,
        limit_order=limit_order,
    )
    instructions.append(instruction)
    
    place_orders = trading.betting.place_orders(
        market_id=market_id, instructions=instructions  # list
    )

    order_response += place_orders.place_instruction_reports

    result = '\n'.join([f"Status: {order.status}, BetId: {order.bet_id}, Average Price Matched: {order.average_price_matched}" for order in order_response])
    result_queue.put(result)

    return(result)

def list_market_catalogue(trading, event_id):

    # Fetch the market catalogue for the event
    market_filter = betfairlightweight.filters.market_filter(
        event_ids=[event_id]
    )

    market_catalogue = trading.betting.list_market_catalogue(
        filter=market_filter,
        market_projection=["MARKET_START_TIME", "EVENT", "RUNNER_DESCRIPTION"],
        sort="MAXIMUM_TRADED",
        max_results=100  # Adjust based on expected number of markets
    )


    market_catalogue_list = []
    # Print the sorted markets
    for market in market_catalogue:
        market_name = market.market_name
        market_id = market.market_id
        start_time = market.market_start_time
        event = market.event.name
        total_matched = market.total_matched
        desc = market.description

        for x in market.runners:
            market_catalogue_list.append({'market_name':market_name, 'market_id': market_id, 'start_time': start_time, 'selection_name': x.runner_name, 'selection_id': x.selection_id, 'event': event, 'total_matched': total_matched, 'desc': desc})

    with open('sample/list_market_catalogue.json', 'w') as json_file:
        json.dump(market_catalogue_list, json_file, indent=4, default=datetime_serializer)

    return(market_catalogue_list)

def list_events(trading):

    # Specify the event type ID (e.g., 7 for horse racing, 1 for soccer)
    event_type_id = "4"
    # Define the time range for market_start_time
    now = datetime.now()
    time_from = (now - timedelta(days=1)).isoformat()  # Current time in ISO format
    time_to = (now + timedelta(days=7)).isoformat()  # 6 hours from now in ISO format

    # Fetch the list of events for the specified event type
    market_filter = betfairlightweight.filters.market_filter(event_type_ids=[event_type_id], market_start_time={"from": time_from, "to": time_to})
    events = trading.betting.list_events(filter=market_filter)

    # Extract and sort events by total matched
    sorted_events = sorted(
        events,
        key=lambda event: event.event.open_date if event.event.open_date else 0,
        reverse=False
    )

    events_list = []
    # Print the sorted events
    for event in sorted_events:
        events_list.append({'event_name':event.event.name, 'date': event.event.open_date, 'event_id': event.event.id})
    
    with open('sample/list_events.json', 'w') as json_file:
        json.dump(events_list, json_file, indent=4, default=datetime_serializer)
    
    return events_list



class Streaming(threading.Thread):
    def __init__(
        self,
        client: betfairlightweight.APIClient,
        market_filter: dict,
        market_data_filter: dict,
        conflate_ms: int = None,
        streaming_unique_id: int = 1000,
    ):
        threading.Thread.__init__(self, daemon=True, name=self.__class__.__name__)
        self.client = client
        self.market_filter = market_filter
        self.market_data_filter = market_data_filter
        self.conflate_ms = conflate_ms
        self.streaming_unique_id = streaming_unique_id
        self.stream = None
        self.output_queue = queue.Queue()
        self.listener = StreamListener(output_queue=self.output_queue)
        self.logger = init_logger('streaming_class')

    @retry(wait=wait_exponential(multiplier=1, min=2, max=20))
    def run(self) -> None:
        self.logger.info("Starting MarketStreaming")
        self.client.login()
        self.stream = self.client.streaming.create_stream(
            unique_id=self.streaming_unique_id, listener=self.listener
        )
        try:
            self.streaming_unique_id = self.stream.subscribe_to_markets(
                market_filter=self.market_filter,
                market_data_filter=self.market_data_filter,
                conflate_ms=self.conflate_ms,
                initial_clk=self.listener.initial_clk,  # supplying these two values allows a reconnect
                clk=self.listener.clk,
            )
            self.stream.start()
        except BetfairError:
            self.logger.error("MarketStreaming run error", exc_info=True)
            raise
        except Exception:
            self.logger.critical("MarketStreaming run error", exc_info=True)
            raise
        self.logger.info("Stopped MarketStreaming %s", self.streaming_unique_id)

    def stop(self) -> None:
        if self.stream:
            self.stream.stop()

def bf_login(logger):
    try:
        with open('/data/betfair_token.key', "rb") as f:
            key = f.read().strip()

        cipher = Fernet(key)
        with open('/data/betfair_token.txt', "rb") as file:
            encrypted_password = file.read().strip()

        with open('/data/betfair_username.txt', "r") as f:
            username = f.read().strip()
        
        with open('/data/betfair_api_key.txt', "r") as f:
            app_key = f.read().strip()

        password = cipher.decrypt(encrypted_password).decode()
        
        trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs='/certs')
        trading.login()
        logger.info(f'Login while streaming successful')
        return trading
    except Exception as e:
        logger.error(f"Error with login while streaming: {e}")
        return None


def stream_price(event_id):
    logger = init_logger('stream_price_process')
    logger.info(f'Start streaming for event_id: {event_id}')
    try:
        redis_client = redis.Redis(host='redis', port=6379)

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

        # check for updates in output queue
        counter = 0
        while True:
            market_books = streaming.output_queue.get()
            for market_book in market_books:
                logger.info(f'New stream for event_id: {event_id}')
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
                        with open('sample/stream_price.json', 'w') as json_file:
                            json.dump(data, json_file, indent=4, default=datetime_serializer)
                        counter+=1

    except Exception as e:
        logger.error(f"Error while streaming event_id: {event_id}\n{e}")
        pass
    
    streaming.stop()
    