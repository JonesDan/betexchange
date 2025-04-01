import redis
from utils import init_logger, stream_price
import multiprocessing

logger = init_logger('stream_price')

redis_client = redis.Redis(host='redis', port=6379)

current_event_id = None

pubsub = redis_client.pubsub()
pubsub.subscribe('event_control')

for message in pubsub.listen():
    if message['type'] == 'message':
        new_event_id = message['data'].decode('utf-8')
        logger.info(f'New event ID: {new_event_id}')
        # Stop the current stream if active
        if current_event_id is not None and new_event_id != current_event_id:
            process.terminate()
            process.join()
            logger.info(f'Terminating existing process for current event id: {current_event_id}')

        # Start a new stream
        current_event_id = new_event_id
        if current_event_id != 'Na':
            logger.info(f'Begin process for event id: {current_event_id}')
            process = multiprocessing.Process(target=stream_price, args=(current_event_id,))
            process.start()
