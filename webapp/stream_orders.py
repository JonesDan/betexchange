from betfairlightweight import StreamListener
import betfairlightweight
from utils import init_logger, list_market_catalogue
from utils_db import upsert_sqlite, calc_order_exposure, create_sample_files, calc_order_exposure_overs, query_sqlite
import queue
import threading
from flask_sse import sse
from flask import Flask
from cryptography.fernet import Fernet
import pickle
import redis
import json

def upload_orders(data, market_id, logger):
    try:
        redis_client = redis.Redis(host='redis', port=6379)

        create_sample_files('raw_stream_order',data)

        price = data['price_size']['Price']
        size = data['price_size']['Size']
        placed_date = data['placed_date'].strftime('%d/%m/%yT%H:%M:%S') if data['placed_date'] else None
        matched_date = data['matched_date'].strftime('%d/%m/%yT%H:%M:%S') if data['matched_date'] else None
        cancelled_date = data['cancelled_date'].strftime('%d/%m/%yT%H:%M:%S') if data['cancelled_date'] else None
        data_adj = {'market_id': market_id, 'price': price, 'size': size, 'placed_date': placed_date, 'matched_date': matched_date, 'cancelled_date': cancelled_date}
        summary = data | data_adj

        logger.info(f'Upsert order data {summary}')
        upsert_sqlite('orders', summary)

        logger.info('Calc selection exposure')
        results = calc_order_exposure(summary['market_id'])
        results = calc_order_exposure_overs(summary['market_id'])
        logger.info(results)

        market_catalogue_dict = query_sqlite(f"SELECT market_id, selection_id, market_name, selection_name FROM market_catalogue m WHERE key = '{summary['market_id']}-{summary['selection_id']}'")
        if len(market_catalogue_dict) > 0:
            summary['market_name'] = market_catalogue_dict[0]['market_name']
            summary['selection_name'] = market_catalogue_dict[0]['selection_name']
            
            if 'OVERS LINE' in summary['market_name']:
                results = calc_order_exposure_overs(summary['market_id'])
            else:
                results = calc_order_exposure(summary['market_id'])

            sse_keys = ['bet_id', 
                        'average_price_matched', 
                        'bsp_liability', 
                        'handicap', 
                        'market_id', 
                        'market_name',
                        'matched_date',
                        'placed_date',
                        'cancelled_date',
                        'order_type', 
                        'persistence_type', 
                        'placed_date', 
                        'selection_id', 
                        'side', 
                        'size_cancelled',
                        'size_lapsed',
                        'size_matched',
                        'size_remaining',
                        'size_voided',
                        'status',
                        'lapsed_date',
                        'lapse_status_reason_code',
                        'cancelled_date',
                        'price',
                        'size']
            
            summary2 = {k:v for k,v in summary.items() if k in sse_keys}

            redis_client.publish('orders', json.dumps({ "data": summary2,"type": "update"}))
            logger.info('Published data to order sse', summary2)

            redis_client.publish('selection_exposure', json.dumps({ "data": results,"type": "update"}))
            logger.info('Published data to selection_exposure sse')
    
    except Exception as e:
        logger.error(f'Error uploading orders {e}', exc_info=True)
        pass



def stream_orders(username, app_key, e, context):

    logger = init_logger('stream_orders')

    with open('/data/e.key', "rb") as f:
        key = f.read().strip()

    cipher = Fernet(key)
    password = cipher.decrypt(e.encode()).decode()
    trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs=f'/certs/{context}')
    resp = trading.login()

    logger.info(f'response from betfair login: {resp.login_status}')

    logger.info('Pull Current Orders')
    current_orders = trading.betting.list_current_orders()
    for order in current_orders.orders:
        data = vars(order)
        market_id = order['market_id']
        upload_orders(data, market_id, logger)

    # create queue
    output_queue = queue.Queue()

    listener = StreamListener(output_queue=output_queue)
    stream = trading.streaming.create_stream(listener=listener)

    # Replace with your actual market filter or just get everything
    stream.subscribe_to_orders()
    t = threading.Thread(target=stream.start, daemon=True)
    t.start()

    logger.info("📡 Listening to Betfair order stream...")

    while True:
        market_data = output_queue.get()

        logger.info('New Order Update')

        for market in market_data:
            market_id = market['streaming_update']['id']
            for order in market['orders']:
                data = vars(order)
                upload_orders(data, market_id, logger)
                    