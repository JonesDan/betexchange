
from flask_sse import sse
import json
import os
import betfairlightweight
import logging
from datetime import datetime
import shelve
import pandas as pd
import numpy as np

def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def init_logger(filename):
    # Logging
    logging.basicConfig(level=logging.INFO
                        , filename=f'{filename}.log'
                        , format='%(asctime)s - %(levelname)s - %(message)s'
                        )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create file handler
    file_handler = logging.FileHandler(f'{filename}.log')
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
        pubsub.subscribe('Orders')
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    update_data = message['data'].decode('utf-8')
                    logger.info(f'Received New Orders Message. Message:{update_data}')
                    update_data = json.loads(update_data)

                    with shelve.open('market_catalogue.db') as cache:
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

                    with shelve.open("orders.db", writeback=True) as db:
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
    for filename in ['market_catalogue.db', 'price_cache.db' ,'orders.db']:
        with shelve.open(filename) as db:
            db.clear()
            