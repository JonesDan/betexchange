import betfairlightweight
from betfairlightweight import filters
from betfairlightweight.filters import market_filter
import time
from dotenv import load_dotenv
import os
import logging
from operator import itemgetter

logging.basicConfig(level=logging.DEBUG)



class bf_exchange:

    def __init__(self, event_type_id):
        # Initialize Betfair API client
        app_key = os.environ['BF_API_KEY']
        username = os.environ['BF_USER']
        password = os.environ['BF_PWD']

        # Create Betfair API client
        self.trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs='/certs')
        # Log in to Betfair API
        self.trading.login()

        self.event_type_id = event_type_id

        pass

    def list_events(self):
        market_filter_params = market_filter(event_type_ids=[self.event_type_id])

        # Get market catalogues
        market_catalogues = self.trading.betting.list_market_catalogue(
            filter=market_filter_params,
            max_results=100,  # Maximum number of markets to retrieve
            market_projection=["EVENT", "MARKET_START_TIME", "RUNNER_METADATA"],
        )

        # Extract and aggregate data
        events = []
        for market in market_catalogues[:1]:
            print(market)
            event_id = market.event.id
            event_name = market.event.name
            market_start_time = market.market_start_time
            total_matched = market.total_matched

            events.append({
                "event_id": event_id,
                "event_name": event_name,
                "market_start_time": market_start_time,
                "total_matched": total_matched,
            })

        # Sort by total matched volume in descending order
        sorted_events = sorted(events, key=itemgetter("total_matched"), reverse=True)
        return sorted_events
    
    def list_markets(self):
        market_filter_params = market_filter(event_type_ids=[self.event_type_id])

        # Get market catalogues
        market_catalogues = self.trading.betting.list_market_catalogue(
            filter=market_filter_params,
            max_results=100,  # Maximum number of markets to retrieve
            market_projection=["EVENT", "MARKET_START_TIME", "RUNNER_METADATA"],
        )

        # Extract and aggregate data
        events = []
        for market in market_catalogues:
            event_id = market.event.id
            event_name = market.event.name
            market_start_time = market.market_start_time
            total_matched = market.total_matched

            events.append({
                "event_id": event_id,
                "event_name": event_name,
                "market_start_time": market_start_time,
                "total_matched": total_matched,
            })

        # Sort by total matched volume in descending order
        sorted_events = sorted(events, key=itemgetter("total_matched"), reverse=True)
        return sorted_events


bf = bf_exchange(4)
events = bf.list_events()

for ev in events:
    print(ev)