from betfairlightweight import StreamListener
import betfairlightweight
from utils import init_logger, list_market_catalogue
from utils_db import upsert_sqlite, calc_order_exposure, create_sample_files, init_db, query_sqlite
import queue
import threading
from flask_sse import sse
from flask import Flask
from cryptography.fernet import Fernet
import pickle
import redis
import json

def stream_orders(username, app_key, e, context):

    logger = init_logger('stream_orders')

    redis_client = redis.Redis(host='redis', port=6379)

    with open('/data/e.key', "rb") as f:
        key = f.read().strip()

    cipher = Fernet(key)
    # password = cipher.decrypt(e).decode()
    password = cipher.decrypt(e.encode()).decode()
    trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs=f'/certs/{context}')
    # trading = betfairlightweight.APIClient(username, e, app_key=app_key, certs=f'/Users/danieljones/betexchange/certs/dev')
    resp = trading.login()

    logger.info(f'response from betfair login: {resp.login_status}')

    app = Flask(__name__)
    app.config["REDIS_URL"] = "redis://redis:6379"
    app.register_blueprint(sse, url_prefix='/stream')

    logger.info('Pull Current Orders')
    current_orders = trading.betting.list_current_orders()
    for order in current_orders.orders:
        data = vars(order)
        price = data['price_size']['Price']
        size = data['price_size']['Size']
        placed_date = data['placed_date'].strftime('%Y-%m-%dT%HH-%MM-%SS')
        data_adj = {'price': price, 'size': size, 'placed_date': placed_date}
        summary = data | data_adj
        upsert_sqlite('orders', summary)
    
    results = calc_order_exposure()
    logger.info(f'Current Order exposure calc example\n{results[0]}')

    # create queue
    output_queue = queue.Queue()

    listener = StreamListener(output_queue=output_queue)
    stream = trading.streaming.create_stream(listener=listener)

    # Replace with your actual market filter or just get everything
    stream.subscribe_to_orders()
    t = threading.Thread(target=stream.start, daemon=True)
    t.start()

    logger.info("📡 Listening to Betfair order stream...")

    with app.app_context():
        while True:
            market_data = output_queue.get()

            with open('/data/selected_markets.pkl', 'rb') as f:
                selected_market_list = pickle.load(f)

            logger.info('New Order Update')

            for market in market_data:
                market_id = market['streaming_update']['id']
                for order in market['orders']:
                    data = vars(order)
                    create_sample_files('raw_stream_order',data)

                    price = data['price_size']['Price']
                    size = data['price_size']['Size']
                    placed_date = data['placed_date'].strftime('%Y-%m-%dT%HH-%MM-%SS')
                    data_adj = {'market_id': market_id, 'price': price, 'size': size, 'placed_date': placed_date}
                    summary = data | data_adj

                    logger.info('Upsert order data')
                    upsert_sqlite('orders', summary)

                    logger.info('Calc selection exposure')
                    results = calc_order_exposure(summary['market_id'])

                    logger.info(results)

                    if market_id in selected_market_list:
                        market_catalogue_dict = query_sqlite(f"SELECT market_id, selection_id, market_name, selection_name FROM market_catalogue m WHERE key = '{data['market_id']}_{data['selection_id']}'")
                        data['market_name'] = market_catalogue_dict[0]['market_name']
                        data['selection_name'] = market_catalogue_dict[0]['selection_name']
                        # sse.publish(data=data, type='update', channel='orders')
                        redis_client.publish('orders', json.dumps({ "data": data,"type": "update"}))
                        logger.info('Published data to order sse')

                        # sse.publish(data=results, type='update', channel='selection_exposure')
                        redis_client.publish('selection_exposure', json.dumps({ "data": results,"type": "update"}))
                        logger.info('Published data to selection_exposure sse')
                        
