
from flask_sse import sse
import json
import os
import betfairlightweight
import logging
from datetime import datetime
import shelve

def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def init_logger(filename):
    # Logging
    logging.basicConfig(level=logging.INFO
                        , filename=f'webapp/{filename}.log'
                        , format='%(asctime)s - %(levelname)s - %(message)s'
                        )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create file handler
    file_handler = logging.FileHandler(f'webapp/{filename}.log')
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
                                with shelve.open('price_cache.db') as cache:
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
        pubsub.subscribe('unmatchedOrders')
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    update_data = message['data'].decode('utf-8')
                    logger.info(f'Received New Orders Message. Message:{update_data}')
                    update_data = json.loads(update_data)

                    data = {'market_id': update_data['market_id'],
                            'selection_id':  update_data['selection_id'],
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
                            }
                    sse.publish(data, type='update', channel='orders')
        except Exception as e:
            logger.error(f"Error Listening: {e}")
            pass
