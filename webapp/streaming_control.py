

from utils import init_logger
import redis
import multiprocessing
import json
from stream_price import stream_price
from stream_orders import stream_orders

logger = init_logger('streaming_control')
redis_client = redis.Redis(host='redis', port=6379)
process_orders = None
process_prices = None

pubsub = redis_client.pubsub()
pubsub.subscribe('event_control')

for message in pubsub.listen():
    if message['type'] == 'message':
        try:
            data_json = message['data'].decode('utf-8')
            data = json.loads(data_json)
            new_event_id = data['event_id']
            logger.info(f'New event ID: {new_event_id}')
            # Stop the current stream if active
            if process_prices is not None:
                process_prices.terminate()
                process_prices.join()
                logger.info(f'Terminating existing prices process for current event id: {current_event_id}')
            
            if process_orders is not None:
                process_orders.terminate()
                process_orders.join()
                logger.info(f'Terminating existing orders process for current event id: {current_event_id}')

            # Start a new stream
            current_event_id = new_event_id
            if current_event_id:
                logger.info(f'Begin prices process for event id: {current_event_id}')
                process_prices = multiprocessing.Process(target=stream_price, args=(data['username'], data['app_key'], data['e'], data['context'], current_event_id,))
                process_prices.start()

                logger.info(f'Begin orders process')
                process_orders = multiprocessing.Process(target=stream_orders, args=(data['username'], data['app_key'], data['e'], data['context']))
                process_orders.start()
            else:
                logger.info(f'current_event_id =  {current_event_id}, No price stream active')
        except Exception as e:
            logger.error(f'error {e}', exc_info=True)
            pass
