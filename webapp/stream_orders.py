import betfairlightweight
from betfairlightweight import StreamListener
from betfairlightweight.streaming.stream import MarketStream
import redis
from utils import Streaming, bf_login, init_logger
import json
import datetime

logger = init_logger('price_orders')

redis_client = redis.Redis(host='redis', port=6379)

trading = bf_login(logger)

# Define a custom listener for streaming orders
class OrderStreamListener(StreamListener):
    def on_data(self, data):
        """Handle incoming streamed order updates."""
        print(f"Received order data: {data}")
        data = json.loads(data)
        try:
            update_date = data['pt']
            if 'oc' in data:
                for market in data['oc']:
                    logger.info(data)
                    logger.info(type(data))
                    market_id = market['id']
                    for orderchanges in market['orc']:
                        selection_id = orderchanges['id']
                        for order in orderchanges['uo']:
                            update_time = datetime.datetime.fromtimestamp(update_date/1000.0).strftime('%Y-%m-%dT%H:%M:%S')
                            summary = order | {'market_id': market_id, 'selection_id': selection_id, 'update_time': update_time}
                            redis_client.publish('Orders', json.dumps(summary))
                        
                        # for order2 in orderchanges['mb']:
                        #     update_time = datetime.datetime.fromtimestamp(update_date/1000.0).strftime('%Y-%m-%dT%H:%M:%S')
                        #     price = order2[0]
                        #     size = order2[1]
                        #     summary2 = {'market_id': market_id, 'selection_id': selection_id, 'update_time': update_time, 'p': price, 's': size, 'sm': size,'sr': 0, 'sl': 0, 'sc': 0, 'sv': 0, 'side': 'B' ,'id': ''}
                        #     redis_client.publish('Orders', json.dumps(summary2))

                        # for order3 in orderchanges['ml']:
                        #     update_time = datetime.datetime.fromtimestamp(update_date/1000.0).strftime('%Y-%m-%dT%H:%M:%S')
                        #     price = order3[0]
                        #     size = order3[1]
                        #     summary3 = {'market_id': market_id, 'selection_id': selection_id, 'update_time': update_time, 'p': price, 's': size, 'sm': size,'sr': 0, 'sl': 0, 'sc': 0, 'sv': 0, 'side': 'L' ,'id': ''}
                        #     redis_client.publish('Orders', json.dumps(summary3))
                            
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
