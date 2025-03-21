
import betfairlightweight
from betfairlightweight import filters
import time
import os
from datetime import datetime, timedelta
import json
from utils import datetime_serializer

def func_list_market_catalogue(trading, event_id):

    # Fetch the market catalogue for the event
    market_filter = betfairlightweight.filters.market_filter(
        event_ids=[event_id]
    )

    market_catalogue = trading.betting.list_market_catalogue(
        filter=market_filter,
        market_projection=["MARKET_START_TIME", "EVENT", "RUNNER_DESCRIPTION"],
        sort="MAXIMUM_TRADED",
        max_results=100  # Adjust based on expected number of markets
    )


    market_catalogue_list = []
    # Print the sorted markets
    for market in market_catalogue:
        market_name = market.market_name
        market_id = market.market_id
        start_time = market.market_start_time
        event = market.event.name
        total_matched = market.total_matched
        desc = market.description

        for x in market.runners:
            market_catalogue_list.append({'market_name':market_name, 'market_id': market_id, 'start_time': start_time, 'selection_name': x.runner_name, 'selection_id': x.selection_id, 'event': event, 'total_matched': total_matched, 'desc': desc})

    with open('sample/list_market_catalogue.json', 'w') as json_file:
        json.dump(market_catalogue_list, json_file, indent=4, default=datetime_serializer)

    return(market_catalogue_list)
