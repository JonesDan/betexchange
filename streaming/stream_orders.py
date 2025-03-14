import betfairlightweight
from betfairlightweight import StreamListener
from betfairlightweight.streaming.stream import MarketStream
import redis
from utils import Streaming, bf_login, init_logger
import json
import datetime

logger = init_logger('price_orders')

redis_client = redis.Redis(host='redis', port=6379)

trading = bf_login()

# Define a custom listener for streaming orders
class OrderStreamListener(StreamListener):
    def on_data(self, data):
        """Handle incoming streamed order updates."""
        print(f"Received order data: {data}")
        data = json.loads(data)
        logger.info(data)
        logger.info(type(data))
        try:
            update_date = data['pt']
            for market in data['oc']:
                market_id = market['id']
                for orderchanges in market['orc']:
                    selection_id = orderchanges['id']
                    for order in orderchanges['uo']:
                        update_time = datetime.datetime.fromtimestamp(update_date/1000.0).strftime('%Y-%m-%dT%H:%M:%S')
                        summary = order | {'market_id': market_id, 'selection_id': selection_id, 'update_time': update_time}
                        redis_client.publish('unmatchedOrders', json.dumps(summary))
        except Exception as e:
            logger.error(f"Error while streaming orders: {e}")
            pass




# Create an order stream connection
listener = OrderStreamListener()
stream = trading.streaming.create_stream(listener=listener)

# Subscribe to the Order Stream
stream.subscribe_to_orders()

# Start the stream
stream.start()
