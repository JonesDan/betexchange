
import json
import betfairlightweight
import logging
from datetime import datetime, timedelta
from betfairlightweight import filters
from utils_db import upsert_sqlite, create_sample_files

def init_logger(filename):
    # Logging
    filepath = f'logs/{filename}.log'

    logger = logging.getLogger(filename)
    logger.setLevel(logging.INFO)

    # Create file handler
    file_handler = logging.FileHandler(filepath, mode='w')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f'Start Logging {filename}')

    return logger

def reset_logger(filename):
    # Remove existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Clear log file
    open(f'logs/{filename}.log', 'w').close()

    logger = init_logger(filename)

            
def place_order(trading, selection_id, b_l, market_id, size, price, sizeMin, result_queue):
    # placing an order
    instructions = []
    order_response = []

    limit_order = filters.limit_order(size=size, price=price, persistence_type="LAPSE", time_in_force="FILL_OR_KILL", min_fill_size=sizeMin)
    instruction = filters.place_instruction(
        order_type="LIMIT",
        selection_id=selection_id,
        side=b_l,
        limit_order=limit_order,
    )
    instructions.append(instruction)
    
    place_orders = trading.betting.place_orders(
        market_id=market_id, instructions=instructions  # list
    )

    order_response += place_orders.place_instruction_reports

    result = '\n'.join([f"Status: {order.status}, BetId: {order.bet_id}, Average Price Matched: {order.average_price_matched}" for order in order_response])
    result_queue.put(result)

    return(result)

def list_market_catalogue(trading, event_id):

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
            data = {'key': f"{market['market_id']}_{x.selection_id}", 'market_name':market_name, 'market_id': market_id, 'start_time': start_time.strftime('%Y-%m-%dTHH:MM:SS'), 'selection_name': x.runner_name, 'selection_id': x.selection_id, 'event': event, 'total_matched': total_matched, 'desc': desc}
            market_catalogue_list.append(data)
            upsert_sqlite('market_catalogue', data)

    create_sample_files('list_market_catalogue', market_catalogue_list)

    return(market_catalogue_list)

def list_events(trading):

    # Specify the event type ID (e.g., 7 for horse racing, 1 for soccer)
    event_type_id = "4"
    # Define the time range for market_start_time
    now = datetime.now()
    time_from = (now - timedelta(days=1)).isoformat()  # Current time in ISO format
    time_to = (now + timedelta(days=7)).isoformat()  # 6 hours from now in ISO format

    # Fetch the list of events for the specified event type
    market_filter = betfairlightweight.filters.market_filter(event_type_ids=[event_type_id], market_start_time={"from": time_from, "to": time_to})
    events = trading.betting.list_events(filter=market_filter)

    # Extract and sort events by total matched
    sorted_events = sorted(
        events,
        key=lambda event: event.event.open_date if event.event.open_date else 0,
        reverse=False
    )

    events_list = []
    # Print the sorted events
    for event in sorted_events:
        events_list.append({'event_name':event.event.name, 'date': event.event.open_date, 'event_id': event.event.id})
    
    create_sample_files('list_events', events_list)

    return events_list

    