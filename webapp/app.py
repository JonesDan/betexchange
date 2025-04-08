from flask import Flask, render_template, Response, jsonify, request, session, flash,redirect, url_for
from flask_session import Session
from flask_sse import sse
from threading import Thread
import redis
import json
import pickle
import os
import betfairlightweight
from datetime import datetime
from utils import init_logger, bf_login, prices_listener, orders_listener, clear_shelve, place_order, list_market_catalogue, list_events, orders_agg, list_current_orders
import shelve
import queue
from cryptography.fernet import Fernet
import time

# Logging
logger = init_logger('app')

app = Flask(__name__)
app.secret_key = 'Pb37TLHgFsrI3XVg'  # Required for session security
app.config["REDIS_URL"] = "redis://redis:6379"  # Update this if using a remote Redis server
app.config["SESSION_COOKIE_SECURE"] = True  # Only allow HTTPS
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"  # Prevent cross-site request attacks
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_USE_SIGNER"] = True  # Prevent tampering
app.config["SESSION_KEY_PREFIX"] = "betfair:"
app.config["SESSION_REDIS"] = redis.StrictRedis(host="redis", port=6379, db=0)
app.config["SESSION_TYPE"] = "redis"

app.register_blueprint(sse, url_prefix='/stream')
context = os.environ[f'APP_CONTEXT']

Session(app)  # Initialize Flask-Session

# Redis Client
redis_client = redis.Redis(host='redis', port=6379)

# Redis - listening to price stream
Thread(target=prices_listener, args=(app, redis_client), daemon=True).start()
Thread(target=orders_listener, args=(app, redis_client), daemon=True).start()

### Flask apps

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        logger.info('Login: GET request for login page')
        return render_template("login.html")
    
    if request.method == "POST":
        # Get info from form
        logger.info('Login: POST request from login page')
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        logger.info(f'Login: username: {username}')

        # Check username and password is filled out
        if not username or not password:
            flash("Username and password required!", "danger")
            return redirect(url_for("login"))
        
        try:
            # Attempt betfair login
            app_key = os.environ[f'BF_API_KEY_{context.upper()}']
            trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs=f'/certs/{context}')
            trading.login()
            session['username'] = username
            session['app_key'] = app_key
            session['session_token'] = trading.session_token

            pwd_file_path = '/data/betfair_token.txt'
            key_file_path = '/data/betfair_token.key'
            user_file_path = '/data/betfair_username.txt'
            api_key_file_path = '/data/betfair_api_key.txt'

            key = Fernet.generate_key()
            cipher = Fernet(key)
            encrypted_password = cipher.encrypt(password.encode())

            with open(pwd_file_path, "wb") as file:
                file.write(encrypted_password)
            with open(key_file_path, "wb") as file:
                file.write(key)
            with open(user_file_path, "w") as file:
                file.write(username)
            with open(api_key_file_path, "w") as file:
                file.write(app_key)

            logger.info(f'Pull current orders')
            list_current_orders(trading, logger, redis_client)

            flash(f"Login Success", "success")

            list_current_orders(trading, logger, redis_client)

            return redirect(url_for("eventList"))
        
        except Exception as e:
            logger.error(f'Login: {e}')
            flash(f"Login failed: {e}", "danger")
            return redirect(url_for("login"))

@app.route('/eventList', methods=["GET"])
def eventList():

    try:
        logger.info(f'EventList: Pull List of Events')
        username = session.get('username', 'No name found')
        app_key = session.get('app_key', 'No app key found')
        session_token = session.get('session_token', 'No session token found')

        trading = betfairlightweight.APIClient(username, 'test', app_key=app_key, certs='/certs')
        trading.session_token = session_token  # Restore session token

        events = list_events(trading)
        logger.info(f'EventList: Number of events pulled {len(events)}')
        redis_client.publish('event_control', "Na")  # Publish to Redis

        return render_template('eventList.html', events=events)
      
    except Exception as e:
        logger.error(f'EventList: {e}')
        flash(f"Error pulling events. Try logging in again", "danger")

        return redirect(url_for("login"))


@app.route('/event/<int:event_id>')
def event_detail(event_id):
    try:
        logger.info(f'Eventdetail: Pull event detail for {event_id}')
        # clear caches
        clear_shelve()

        # Get Sessions details
        username = session.get('username', 'No name found')
        app_key = session.get('app_key', 'No app key found')
        session_token = session.get('session_token', 'No session token found')
        
        trading = betfairlightweight.APIClient(username, 'test', app_key=app_key, certs='/certs')
        trading.session_token = session_token  # Restore session token
        
        # Publish event id for price streaming
        logger.info(f'Eventdetail: Publish {event_id} to redis for price stream')
        redis_client.publish('event_control', str(event_id))  # Publish to Redis
        
        # Get markets and build market cache
        market_data = list_market_catalogue(trading, event_id)
        market_selection_ids = {}
        market_ids_list = []
        logger.info(f'Eventdetail: Pulled {len(market_data)} Markets')
        for market in market_data:
            market_id = market['market_id']
            summary = {'selection_id': market['selection_id'], 'selection_name':market['selection_name'], 'market_name':market['market_name']}
            # Create list of unique market ids for table
            if market_id not in market_selection_ids:
                market_ids_list.append({'id': market['market_id'], 'market_name': market['market_name'], 'total_matched': f"{market['total_matched']:,}"})

            market_selection_ids.setdefault(market_id, []).append(summary)

        with shelve.open('shelve/market_catalogue.db') as cache:
            cache['market_catalogue'] = market_selection_ids

        with open('sample/market_selection_ids.json', 'w') as json_file:
            json.dump(market_selection_ids, json_file, indent=4)

        event_name = market_data[0]['event']

        return render_template('event_details.html', markets=market_ids_list, event_name=event_name)
    
    except Exception as e:
        logger.error(f'Eventdetail: {e}')
        flash(f"Error pulling event details. Try logging in again", "danger")

        return redirect(url_for("login"))


@app.route('/get_prices', methods=["POST"])
def get_prices():
    market_id = request.json.get("marketid", [])

    with shelve.open('shelve/market_catalogue.db') as cache:
        selections = dict(cache['market_catalogue'])

    with shelve.open('shelve/selected_markets.db') as cache:
        my_list = cache.get("my_list", [])  # Default to an empty list if key not found
        my_list.append(str(market_id))
        cache["my_list"] = my_list  # Reassign to update the shelve entry

    with open('sample/selected_markets.json', 'w') as json_file:
        json.dump(my_list, json_file, indent=4)

    summary = []
    updatetimeList = []
    with shelve.open('shelve/price_cache.db') as cache:
        db = dict(cache)

    for s in selections[str(market_id)]:
        logger.info(f'selection {s}')
        for b_l in ['batb','batl']:
            selection_id = s['selection_id']
            id = f"{market_id}-{selection_id}-{b_l}"

            priceList = [db[f"{id}-{level}"]['price'] if f"{id}-{level}" in db else 0 for level in range(10)] + ['Custom']
            sizeList = [db[f"{id}-{level}"]['size'] if f"{id}-{level}" in db else 0 for level in range(10)] + [0]
            updatetimeList.append(max([db[f"{id}-{level}"]['update_time'] if f"{id}-{level}" in db else '0' for level in range(10)]))

            b_l2 = 'BACK' if b_l == 'batb' else 'LAY'

            orders_agg_dict = orders_agg()
            if f"{market_id}_{selection_id}" in orders_agg_dict:
                if b_l == 'batb':
                    ex = orders_agg_dict[f"{market_id}_{selection_id}"]['exp_wins']
                else:
                    ex = orders_agg_dict[f"{market_id}_{selection_id}"]['exp_lose']
            else:
                ex = 0

            summary.append({'id': id,'market_id': market_id, 'selection_id': selection_id,'market_name': s['market_name'],'selection_name':s['selection_name'],'b_l': b_l2, 'priceList': priceList, 'sizeList':sizeList,'ex':ex})

    updatetime = max(updatetimeList) if len(updatetimeList) > 0 else ""

    #get current orders
    with shelve.open("shelve/orders.db", writeback=True) as db:
        order_summary = db.get("my_dict", {})
    
    logger.info(f'Eventdetail: Pulled {len(order_summary.keys())} existing orders')
    for order in order_summary.keys():
        if order_summary[order]['market_id'] in selections:
            sse.publish(order_summary[order], type='update', channel='orders')

    logger.info(f'data for betting table {summary}')
    return jsonify({'selected_markets': summary, 'update_time': updatetime})

# Pull Market data

# Process orders
@app.route('/place_orders', methods=["POST"])
def place_orders():

    # global trading
    username = session.get('username', 'No name found')
    app_key = session.get('app_key', 'No app key found')
    session_token = session.get('session_token', 'No session token found')
    
    trading = betfairlightweight.APIClient(username, 'test', app_key=app_key, certs='/certs')
    trading.session_token = session_token  # Restore session token

    result_queue = queue.Queue()
    threads = []
    
    order_details = request.get_json('order_details')

    logger.info(f'order_details\n{order_details}')

    with shelve.open('shelve/price_cache.db') as cache:
        price_dict = dict(cache)
    
    for order in order_details['order_details']:
        market_id = order.split('-')[0]
        selection_id = order.split('-')[1]
        b_l = order.split('-')[2]
        b_l2 = 'BACK' if b_l == 'batb' else 'LAY' if b_l == 'batl' else ''
        price = float(price_dict[f'{market_id}-{selection_id}-batl-0'])


        size = float(order_details['order_details'][order]['size'])
        sizeMin = float(order_details['order_details'][order]['sizeMin'])
        thread = Thread(target=place_order, args=(trading, selection_id, b_l2, market_id, size, price, sizeMin, result_queue))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to finish
    for thread in threads:
        thread.join()
    
     # Collect results from the queue
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    response_str = "\n\n".join(results)

    logger.info(f'response_str: {response_str}')

    # Example: Process IDs (you can modify this function)
    return jsonify({"message": f"{response_str}"})

# Process orders
@app.route('/hedge_orders', methods=["POST"])
def hedge_orders():
    # global trading
    username = session.get('username', 'No name found')
    app_key = session.get('app_key', 'No app key found')
    session_token = session.get('session_token', 'No session token found')
    
    trading = betfairlightweight.APIClient(username, 'test', app_key=app_key, certs='/certs')
    trading.session_token = session_token  # Restore session token

    result_queue = queue.Queue()
    threads = []
    
    order_details = request.get_json('order_details')

    logger.info(f'hedge_order_details\n{order_details}')
    
    for order in order_details['order_details']:
        market_id = order.split('-')[0]
        selection_id = order.split('-')[1]
        b_l2 = 'LAY'
        price = float(order_details['order_details'][order]['price'])
        size = float(order_details['order_details'][order]['size'])
        sizeMin = float(order_details['order_details'][order]['sizeMin'])
        thread = Thread(target=place_order, args=(trading, selection_id, b_l2, market_id, size, price, sizeMin, result_queue))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to finish
    for thread in threads:
        thread.join()


# Run App
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')