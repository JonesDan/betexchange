import betfairlightweight
from betfairlightweight import filters
import time
import os
from datetime import datetime, timedelta

# create trading instance (app key must be activated for streaming)
app_key = os.environ['BF_API_KEY']
username = os.environ['BF_USER']
password = os.environ['BF_PWD']
trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs='/certs')

# Log in to Betfair API
trading.login()
# Fetch the list of events for the specified event type
current_orders = trading.betting.list_current_orders()

if current_orders.orders:
    for order in current_orders.orders:
        print(f"Market ID: {order.market_id}")
        print(f"Order ID: {order.bet_id}")
        print(f"Status: {order.status}")
        print(f"Side: {order.side}")
        print(f"Size Matched: {order.size_matched}")
        print(f"Remaining Size: {order.size_remaining}")
        print(f"Price Requested: {order.price_size.price}")
        print(f"Order Placed Time: {order.placed_date}")
        print("-" * 50)
else:
    print("No current orders found.")