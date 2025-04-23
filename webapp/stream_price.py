
from flask_sse import sse
import betfairlightweight
from betfairlightweight.filters import (
    streaming_market_filter,
    streaming_market_data_filter,
)
from multiprocessing import Queue
import threading
from tenacity import retry, wait_exponential
from betfairlightweight import StreamListener
from betfairlightweight import BetfairError
from utils import init_logger
from utils_db import upsert_sqlite, create_sample_files
from flask import Flask
import os
from cryptography.fernet import Fernet
import pickle
import time


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
        self.output_queue = Queue()
        self.listener = StreamListener(output_queue=self.output_queue)
        self.logger = init_logger('streaming_class')

    @retry(wait=wait_exponential(multiplier=1, min=2, max=20))
    def run(self) -> None:
        self.logger.info("Starting MarketStreaming")
        self.client.login()
        self.stream = self.client.streaming.create_stream(
            unique_id=self.streaming_unique_id, listener=self.listener
        )

        self.logger.info("done first couple of steps")
        try:
            self.streaming_unique_id = self.stream.subscribe_to_markets(
                market_filter=self.market_filter,
                market_data_filter=self.market_data_filter,
                conflate_ms=self.conflate_ms,
                initial_clk=self.listener.initial_clk,  # supplying these two values allows a reconnect
                clk=self.listener.clk,
            )
            self.logger.info("subscribed")
            self.stream.start()
            self.logger.info("started")
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

def stream_price(username, app_key, e, context, event_id):
    try:
        logger = init_logger('stream_price')

        with open('/data/e.key', "rb") as f:
            key = f.read().strip()

        cipher = Fernet(key)
        password = cipher.decrypt(e).decode()

        trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs=f'/certs/{context}')

        # trading = betfairlightweight.APIClient(username, e, app_key=app_key, certs=f'/Users/danieljones/betexchange/certs/{context}')
        resp = trading.login()

        logger.info(f'response from betfair login: {resp.login_status}')

        app = Flask(__name__)
        app.config["REDIS_URL"] = "redis://redis:6379"
        app.register_blueprint(sse, url_prefix='/stream')

        # create filters (GB WIN racing)
        market_filter = streaming_market_filter(
            event_ids=[str(event_id)]
        )
        market_data_filter = streaming_market_data_filter(
            fields=["EX_BEST_OFFERS", "EX_MARKET_DEF"], ladder_levels=10
        )

        # create streaming object
        streaming = Streaming(client=trading, market_filter=market_filter, market_data_filter=market_data_filter)

        # start streaming (runs in new thread and handles any errors)
        streaming.start()

        logger.info(f"📡 Listening to Betfair price stream...for event {event_id}")

        # check for updates in output queue
        # with app.app_context():
        while True:
            logger.info("📡 Still Listening...")
            for x in range(100):
                logger.info(f"{x}")
                time.sleep(1)
            market_books = streaming.output_queue.get()
            # try:
            #     with open('data/selected_markets.pkl', 'rb') as f:
            #         selected_market_list = pickle.load(f)
            # except Exception as e:
            #     logger.error(f'{e}')
            #     pass
            selected_market_list = []
            logger.info('New Price Update')
            for market_book in market_books:
                data = market_book.streaming_update
                create_sample_files('raw_stream_price',data)

                print(vars(market_book))
                
                publish_time = market_book.publish_time
                if 'rc' in data:
                    market_id = data['id']
                    for selection in data['rc']:
                        for lay in selection.get('batl',[]):
                            summary = {'key': f"{market_id}-{selection['id']}-LAY-{lay[0]}",
                                    'market_id': data['id'],
                                    'selection_id': selection['id'],
                                    'side': 'LAY',
                                    'level': lay[0],
                                    'price': lay[1],
                                    'size': lay[2],
                                    'publish_time': publish_time.isoformat()
                                    }
                            
                            logger.info(f'Upsert price data {summary}')
                            upsert_sqlite('price', summary)
                            if data['id'] in selected_market_list:
                                sse.publish(data=summary, type='update', channel='prices')
                                
                        for back in selection.get('batb',[]):
                            summary = {'key': f"{market_id}-{selection['id']}-BACK-{back[0]}",
                                    'market_id': data['id'],
                                    'selection_id': selection['id'],
                                    'side': 'BACK',
                                    'level': back[0],
                                    'price': back[1],
                                    'size': back[2],
                                    'publish_time': publish_time.isoformat()
                                    }
                            
                            logger.info(f'Upsert price data {summary}')
                            upsert_sqlite('price', summary)
                            if data['id'] in selected_market_list:
                                sse.publish(data=summary, type='update', channel='prices')
                                logger.info('Published data to prices sse')

    except Exception as e:
        logger.error(f"Error while streaming event_id: {event_id}\n{e}")
        pass

# with open('data/selected_markets.pkl', 'wb') as f:
#     pickle.dump([1.242779508], f)
# stream_price('jonesy2005', 'mzOge8pJMvubUDpV', 'U6jGY=wevtX8$C!', 'DEV', 34238027)