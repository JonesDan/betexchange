

from flask import Flask, render_template, Response, jsonify, request, session, flash,redirect, url_for
from flask_session import Session
from bf_api.list_events import list_events
from bf_api.list_market_catalogue import func_list_market_catalogue
from bf_api.place_orders import place_order
from celery import Celery
from flask_sse import sse
from threading import Thread
import redis
import json
import pickle
import os
import betfairlightweight
import logging
import collections
from datetime import datetime
from utils import init_logger, bf_login, prices_listener, orders_listener
import shelve
import queue
from cryptography.fernet import Fernet
import ssl

# Logging
logger = init_logger('app')

# trading  = bf_login()

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

Session(app)  # Initialize Flask-Session

# Redis Client
redis_client = redis.Redis(host='redis', port=6379)

# Redis - listening to price stream
Thread(target=prices_listener, args=(app, redis_client), daemon=True).start()
Thread(target=orders_listener, args=(app, redis_client), daemon=True).start()

# Redis - listening to order stream

### Flask apps



@app.route("/", methods=["GET", "POST"])
def login():
    # global trading 
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password required!", "danger")
            return redirect(url_for("login"))

        # Get Token from API
        # trading  = bf_login(username, password)

        try:
            app_key = os.environ['BF_API_KEY']
            # username = os.environ['BF_USER']
            # password = os.environ['BF_PWD']
            trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs='/certs')
            trading.login()

            if trading:
                session["username"] = username
                session["pword"] = password
                session["session_token"] = trading.session_token

                logger.info(f'username: {username}\n app_key: {app_key}')

                pwd_file_path = '/data/betfair_token.txt'
                key_file_path = '/data/betfair_token.key'

                key = Fernet.generate_key()
                cipher = Fernet(key)
                encrypted_password = cipher.encrypt(password.encode())

                with open(pwd_file_path, "wb") as file:
                    file.write(encrypted_password)

                with open(key_file_path, "wb") as file:
                    file.write(key)

                print("Token updated securely.")
                session["app_key"] = app_key
                flash("Login successful!", "success")
                return redirect(url_for("eventList"))
        except Exception as e:
            print(f"Login failed: {str(e)}")
            flash(f"Login failed: {str(e)}", "danger")

    return render_template("login.html")

# Home - pick events
@app.route('/eventList')
def eventList():
    # global trading
    if "session_token" not in session:
        flash("You must log in first!", "warning")
        return redirect(url_for("login"))

    flash("Login successful!", "success")
    username = session.get('username', 'No name found')
    app_key = session.get('app_key', 'No app key found')
    session_token = session.get('session_token', 'No session token found')

    logger.info(f'username: {username}\n app_key: {app_key}\n session_token: {session_token}')
    
    trading = betfairlightweight.APIClient(username, 'test', app_key=app_key, certs='/certs')
    trading.session_token = session_token  # Restore session token


    logger.info('Load homepage')
    events = list_events(trading)
    num_of_events = len(events)
    logger.info(f'Load Events: Number of events {num_of_events}')

    redis_client.publish('event_control', "Na")  # Publish to Redis

    return render_template('events.html', events=events)

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    # global trading
    if "session_token" not in session:
        flash("You must log in first!", "warning")
        return redirect(url_for("login"))

    username = session.get('username', 'No name found')
    app_key = session.get('app_key', 'No app key found')
    session_token = session.get('session_token', 'No session token found')

    logger.info(f'username: {username}\n app_key: {app_key}\n session_token: {session_token}')
    
    trading = betfairlightweight.APIClient(username, 'test', app_key=app_key, certs='/certs')
    trading.session_token = session_token  # Restore session token
    
    logger.info(f'Load Event Page. Event ID {event_id}')
    redis_client.publish('event_control', str(event_id))  # Publish to Redis
    
    try:
        data = func_list_market_catalogue(trading, event_id)
        num_of_markets = len(data)
        logger.info(f'Pull Markets. Num of markets {num_of_markets}')
        market_selection_ids = {}
        for market in data:
            market_id = market['market_id']
            summary = {'selection_id': market['selection_id'], 'selection_name':market['selection_name'], 'market_name':market['market_name']}
            if market_id not in market_selection_ids:
                market_selection_ids[market_id] = [summary]
            else:
                market_selection_ids[market_id].append(summary)

        with shelve.open('market_catalogue.db') as cache:
            cache['market_catalogue'] = market_selection_ids
        
    except Exception as e:
        logger.error(f"Error while pulling markets: {e}")
        pass
            
    market_catalogue_distinct_ids = []
    market_catalogue_distinct = []
    for m in data:
        if m['market_id'] not in market_catalogue_distinct_ids:
            market_catalogue_distinct_ids.append(m['market_id'])
            market_catalogue_distinct.append({'id': m['market_id'], 'market_name': m['market_name'], 'total_matched': f"{m['total_matched']:,}"})

    event_name = data[0]['event']
    return render_template('event_details.html', markets=market_catalogue_distinct, event_name=event_name)

@app.route('/get_prices2', methods=["POST"])
def get_prices2():
    market_id = request.json.get("marketid", [])

    with shelve.open('market_catalogue.db') as cache:
        selections = dict(cache['market_catalogue'])
    logger.info(f'selected market ids {selections}')
    summary = []
    updatetimeList = []
    with shelve.open('price_cache.db') as cache:
        db = dict(cache)

    for s in selections[str(market_id)]:
        logger.info(f'selection {s}')
        for b_l in ['batb','batl']:
            selection_id = s['selection_id']
            id = f"{market_id}-{selection_id}-{b_l}"
            logger.info(f'id {id}')
            priceList = [db[f"{id}-{level}"]['price'] if f"{id}-{level}" in db else 0 for level in range(10)] + ['Custom']
            sizeList = [db[f"{id}-{level}"]['size'] if f"{id}-{level}" in db else 0 for level in range(10)] + [0]
            updatetimeList.append(max([db[f"{id}-{level}"]['update_time'] if f"{id}-{level}" in db else '0' for level in range(10)]))

            b_l2 = 'BACK' if b_l == 'batb' else 'LAY'

            summary.append({'id': id,'market_id': market_id, 'selection_id': selection_id,'market_name': s['market_name'],'selection_name':s['selection_name'],'b_l': b_l2, 'priceList': priceList, 'sizeList':sizeList })

    updatetime = max(updatetimeList) if len(updatetimeList) > 0 else ""

    return jsonify({'selected_markets': summary, 'update_time': updatetime})

# Pull Market data

# Process orders
@app.route('/place_orders', methods=["POST"])
def place_orders():
    # global trading
    username = session.get('username', 'No name found')
    app_key = session.get('app_key', 'No app key found')
    session_token = session.get('session_token', 'No session token found')

    logger.info(f'username: {username}\n app_key: {app_key}\n session_token: {session_token}')
    
    trading = betfairlightweight.APIClient(username, 'test', app_key=app_key, certs='/certs')
    trading.session_token = session_token  # Restore session token

    result_queue = queue.Queue()
    threads = []
    
    order_details = request.get_json('order_details')

    logger.info(f'order_details\n{order_details}')
    
    for order in order_details['order_details']:
        market_id = order.split('-')[0]
        selection_id = order.split('-')[1]
        b_l = order.split('-')[2]
        b_l2 = 'BACK' if b_l == 'batb' else 'LAY' if b_l == 'batl' else ''
        price = float(order_details['order_details'][order]['price'])
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


# Run App
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')