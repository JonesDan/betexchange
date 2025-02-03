import betfairlightweight
from betfairlightweight import filters
import time
import os
from datetime import datetime, timedelta

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
    
    return events_list

