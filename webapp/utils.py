
import json
import betfairlightweight
import logging
from datetime import datetime, timedelta
from betfairlightweight import filters
from utils_db import upsert_sqlite, create_sample_files, query_sqlite
import os
from cryptography.fernet import Fernet

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

            
def place_order(trading, selection_id, b_l, market_id, size, price, result_queue):
    try:
        # placing an order
        instructions = []
        order_response = []

        # limit_order = filters.limit_order(size=size, price=price, persistence_type="LAPSE", time_in_force="FILL_OR_KILL", min_fill_size=sizeMin)
        limit_order = filters.limit_order(size=round(size, 2), price=round(price, 2), persistence_type="LAPSE")
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

        result = '\n'.join([f"Status: {order.status}, BetId: {order.bet_id}, Average Price Matched: {order.average_price_matched}, Error Code: {order.error_code}" for order in order_response])
    except Exception as e:
        result = f"Error placing order {e}"
        pass

    result_queue.put(result)

def cancel_order(trading, bet_id, market_id, sr, result_queue):
    # cancelling an order
    try:
        instruction = filters.cancel_instruction(bet_id=bet_id, size_reduction=round(sr,2))
        cancel_order = trading.betting.cancel_orders(
            market_id=market_id, instructions=[instruction]
        )

        print(cancel_order.status)
        for cancel in cancel_order.cancel_instruction_reports:
            print(
                "Status: %s, Size Cancelled: %s, Cancelled Date: %s"
                % (cancel.status, cancel.size_cancelled, cancel.cancelled_date)
            )
            result =  "Status: %s, Size Cancelled: %s, Cancelled Date: %s" % (cancel.status, cancel.size_cancelled, cancel.cancelled_date)

    except Exception as e:
        result = f"Error placing order {e}"
        pass

    result_queue.put(result)

def cancel_all_orders(trading, result_queue):
    # cancelling an order
    try:
        # instruction = filters.cancel_instruction()
        cancel_order = trading.betting.cancel_orders(
            instructions=[]
        )
        result =  f"All Unmatched Orders Cancelled. Status {cancel_order.status}"

    except Exception as e:
        result = f"Error placing order {e}"
        pass

    result_queue.put(result)

def list_market_catalogue(trading, event_id_list):

    # Fetch the market catalogue for the event
    market_filter = betfairlightweight.filters.market_filter(
        event_ids=event_id_list
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
            data = {'key': f"{market['market_id']}-{x.selection_id}", 'market_name':market_name, 'market_id': market_id, 'start_time': start_time.strftime('%Y-%m-%dTHH:MM:SS'), 'selection_name': x.runner_name, 'selection_id': x.selection_id, 'event': event, 'total_matched': total_matched, 'desc': desc}
            market_catalogue_list.append(data)
            upsert_sqlite('market_catalogue', data)

    create_sample_files('list_market_catalogue', market_catalogue_list[0])

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

    
    create_sample_files('list_events', events_list[0])

    return events_list

def get_exposure_overs(market_id):
    selection_exp_overs = query_sqlite(f"""
                        WITH numbered AS (
                                    SELECT
                                        runs,
                                        profit,
                                        runs - ROW_NUMBER() OVER (PARTITION BY profit ORDER BY runs) AS grp
                                    FROM selection_exposure_overs
                                       WHERE market_id = {market_id}
                                    ),
                                    grouped AS (
                                    SELECT
                                        MIN(runs) AS start_run,
                                        MAX(runs) AS end_run,
                                        profit
                                    FROM numbered
                                    GROUP BY profit, grp
                                    ),
                                    max_run AS (
                                    SELECT MAX(runs) AS max_run FROM selection_exposure_overs
                                    ),
                                    formatted AS (
                                    SELECT
                                        CASE 
                                        WHEN start_run = end_run AND end_run = (SELECT max_run FROM max_run)
                                            THEN CAST(end_run AS TEXT) || '+'
                                        WHEN start_run = end_run
                                            THEN CAST(start_run AS TEXT)
                                        WHEN end_run = (SELECT max_run FROM max_run)
                                            THEN CAST(start_run AS TEXT) || '-' || CAST(end_run AS TEXT) || '+'
                                        ELSE
                                            CAST(start_run AS TEXT) || '-' || CAST(end_run AS TEXT)
                                        END AS runs,
                                        profit,
                                        start_run
                                    FROM grouped
                                    )
                                    SELECT * FROM formatted
                                    ORDER BY start_run;
                                """)
    
    return selection_exp_overs

def get_betfair_client_from_flask_session(session):
    username = session.get('username', 'No name found')
    context = session.get('context', 'No name found')
    app_key = session.get('app_key', 'No name found')
    e = session.get('e', 'No name found')
    session_token = session.get('session_token', 'No session token found')

    trading = betfairlightweight.APIClient(username, 'test', app_key=app_key, certs=f'/certs/{context}')
    trading.session_token = session_token  # Restore session token
    trading.keep_alive()

    return trading
