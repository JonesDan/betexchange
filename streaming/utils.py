import logging
import queue
import threading
from tenacity import retry, wait_exponential
import betfairlightweight
from betfairlightweight import StreamListener
from betfairlightweight import BetfairError
import os
from cryptography.fernet import Fernet
import time


def init_logger(filename):
    # Logging
    logging.basicConfig(level=logging.INFO
                        , filename=f'streaming/{filename}.log'
                        , format='%(asctime)s - %(levelname)s - %(message)s'
                        )
    logger = logging.getLogger(filename)
    logger.setLevel(logging.INFO)

    # Create file handler
    file_handler = logging.FileHandler(f'streaming/{filename}.log')
    file_handler.setLevel(logging.DEBUG)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


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
        self.logger = init_logger('price_streaming_class')

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

def wait_for_file(file_path, check_interval=1):
    """Waits for a file to be populated before proceeding."""
    while not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        print(f"Waiting for file {file_path} to be populated...")
        time.sleep(check_interval)  # Wait before checking again

    print(f"File {file_path} is ready!")
    return True  # Continue execution

def bf_login(logger):
    # create trading instance (app key must be activated for streaming)

    # wait for password files to be populated
    wait_for_file('/data/betfair_token.key', check_interval=1)
    try:
        app_key = os.environ['BF_API_KEY']
        with open('/data/betfair_token.key', "rb") as f:
            key = f.read().strip()

        cipher = Fernet(key)
        with open('/data/betfair_token.txt', "rb") as file:
            encrypted_password = file.read().strip()  # Remove any leading/trailing whitespace

        with open('/data/betfair_username.txt', "r") as f:
            username = f.read().strip()
        password = cipher.decrypt(encrypted_password).decode()
        
        logger.info('username=\n'+username)
        trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs='/certs')
        # trading.session_token = token

        # Log in to Betfair API
        trading.login()
    except Exception as e:
        logger.error(f"Error while streaming: {e}")
        pass

    return trading
    