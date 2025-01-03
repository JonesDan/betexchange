import betfairlightweight
from betfairlightweight import filters
import time
from dotenv import load_dotenv
import os
import logging
logging.basicConfig(level=logging.DEBUG)



class bf_exchange:

    def __init__(self):
        # Initialize Betfair API client
        app_key = os.environ['BF_API_KEY']
        username = os.environ['BF_USER']
        password = os.environ['BF_PWD']

        # Create Betfair API client
        self.trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs='/certs')
        # Log in to Betfair API
        self.trading.login()

        pass


bf = bf_exchange()