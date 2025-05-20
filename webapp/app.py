from flask import Flask, render_template, jsonify, request, session, flash,redirect, url_for
from flask_session import Session
from flask_sse import sse
from threading import Thread
import redis
import os
import betfairlightweight
from utils import init_logger, place_order, cancel_order, cancel_all_orders, list_market_catalogue, list_events, get_betfair_client_from_flask_session, get_exposure_overs
from utils_db import query_sqlite, init_db, delete_sample_files, init_selected_markets
import queue
from cryptography.fernet import Fernet
import pickle
import time
import json
from datetime import datetime
from millify import millify
import urllib.parse

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
# current_process = {'process_price': None, 'process_order': None}

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
            session.permanent = True
            session['username'] = username
            session['app_key'] = app_key
            session['session_token'] = trading.session_token
            logger.info(f'Login: Successful Login')

            key = Fernet.generate_key()
            cipher = Fernet(key)
            encrypted_password = cipher.encrypt(password.encode())
            encrypted_password_str = encrypted_password.decode()  # Convert bytes to string
            session['e'] = encrypted_password_str

            with open('/data/e.key', "wb") as file:
                file.write(key)

            results = delete_sample_files()
            logger.info(f'Login: Delete sample files output {results}')

            return redirect(url_for("eventList"))
        
        except Exception as e:
            logger.error(f'Login: error {e}', exc_info=True)
            flash(f"Login failed: {e}", "danger")
            return redirect(url_for("login"))

@app.route('/eventList', methods=["GET"])
def eventList():

    try:
        logger.info(f'EventList: Pull List of Events')

        trading = get_betfair_client_from_flask_session(session)

        events = list_events(trading)
        logger.info(f'EventList: Number of events pulled {len(events)}')

        return render_template('eventList.html', events=events)
      
    except Exception as e:
        logger.error(f'EventList: error {e}', exc_info=True)
        flash(f"Error pulling EventList: {e}", "danger")
        return redirect(url_for("login"))


@app.route('/eventList/<event_name>/<int:event_id>')
def eventDetail(event_name, event_id):
    try:
        logger.info(f'EventDetail: Pull event detail for {event_id}')

        logger.info(f'EventDetail: Create sqlite tables')
        results = init_db()
        logger.info(f'EventDetail: init_db results {results}')

        init_selected_markets()
        logger.info(f'EventDetail: Clear selected_markets shelve')

        return render_template('eventDetail.html', event_name=event_name)
    
    except Exception as e:
        logger.error(f'Eventdetail: error {e}', exc_info=True)
        flash(f"Error pulling EventDetail: {e}", "danger")
        return redirect(url_for("eventList"))

@app.route('/get_markets', methods=['POST'])
def get_markets():
    try:
        data = request.get_json()
        url = data.get('url')
        event_id = url.split('/')[-1]

        logger.info(f'refreshMarkets: Pull Markets. Event_id {event_id}')

        trading = get_betfair_client_from_flask_session(session)
        list_market_catalogue(trading, [event_id])
        
        market_ids_list = query_sqlite(f"SELECT DISTINCT event, market_id, market_name, total_matched FROM market_catalogue order by total_matched desc")

        for market in market_ids_list:
            market['total_matched'] = millify(market['total_matched'], precision=2)
        
        update_time = datetime.now().strftime('%Y-%M-%dT%H:%M:%S')

        return jsonify({'markets': market_ids_list, 'update_time': update_time})
        
    except Exception as e:
        logger.error(f'refreshMarkets: error {e}', exc_info=True)
        flash(f"Error refreshing markets: {e}", "danger")
        return redirect(url_for("eventList"))

@app.route('/get_prices', methods=["POST"])
def get_prices():

    try:
        market_id = request.json.get("marketid", [])

        logger.info(f'getPrices: Pull prices for {market_id}')

        attempt = 0
        prices = []
        while len(prices) == 0 and attempt < 3:
            prices = query_sqlite(f"""
                                SELECT 
                                    p.market_id AS market_id,
                                    m.market_name AS market_name,
                                    p.selection_id AS selection_id,
                                    m.selection_name AS selection_name,
                                    p.side AS side,
                                    MAX(p.publish_time) AS publish_time,
                                    GROUP_CONCAT(p.price) AS priceList,
                                    GROUP_CONCAT(p.size) AS sizeList,
                                    GROUP_CONCAT(p.level) AS levelList,
                                    CASE WHEN p.side = 'BACK' THEN printf('%.2f', AVG(s.exposure)) ELSE 0 END AS exposure
                                FROM (
                                    SELECT 
                                        market_id, 
                                        selection_id, 
                                        side, 
                                        publish_time, 
                                        price, 
                                        size, 
                                        level
                                    FROM price
                                    ORDER BY market_id, selection_id, side, level
                                ) p
                                JOIN market_catalogue m
                                    ON p.market_id = m.market_id AND p.selection_id = m.selection_id
                                LEFT JOIN selection_exposure s
                                    ON m.market_id = s.market_id  AND m.selection_id = s.selection_id
                                WHERE p.market_id = '{market_id}'
                                GROUP BY p.market_id, m.market_name, p.selection_id, m.selection_name, p.side
                                """)
            attempt+=1
            time.sleep(1)
        
        
        logger.info(f'getPrices: Convert Prices and Size to List: {prices[0]}')

        for price in prices:
            price['priceList'] = price['priceList'].split(',')
            price['sizeList'] = [millify(size) for size in price['sizeList'].split(',')]

        exposure_overs = get_exposure_overs(market_id)
        session_prefixes = ('price-', 'size-', 'shortcut-', 'shortcut-hedge-')
        sessionValues = {key: value for key, value in session.items() if key.startswith(session_prefixes)}

        logger.info(f'getPrices: sessionValues: {sessionValues}')
        return jsonify({'selected_markets': prices,'sessionValues': sessionValues,'exposure_overs': exposure_overs, 'publish_time': prices[0]['publish_time']})
    
    except Exception as e:
        logger.error(f'getPrices: error {e}', exc_info=True)
        pass


@app.route('/get_orders')
def get_orders():
    try:
        logger.info(f'getOrders: Pull existing orders')
        attempt = 0
        existing_orders = []
        while len(existing_orders) == 0 and attempt < 3:
            existing_orders = query_sqlite("""
                                        SELECT 
                                        o.bet_id, 
                                        m.market_name, 
                                        m.selection_name,
                                        o.placed_date,
                                        o.matched_date,
                                        o.cancelled_date, 
                                        o.side,
                                        o.status,
                                        printf('%.2f', o.price) AS price,
                                        printf('%.2f', o.size) AS size,
                                        printf('%.2f', o.average_price_matched) AS average_price_matched,
                                        printf('%.2f', o.size_matched) AS size_matched,
                                        printf('%.2f', o.size_remaining) AS size_remaining,
                                        printf('%.2f', o.size_lapsed) AS size_lapsed,
                                        printf('%.2f', o.size_cancelled) AS size_cancelled,
                                        printf('%.2f', o.size_voided) AS size_voided
                                        FROM
                                        orders o
                                        JOIN market_catalogue m ON o.market_id = m.market_id AND o.selection_id = m.selection_id
                                        """)
            attempt+=1
            time.sleep(1)
        
        logger.info(f'getOrders: example {existing_orders[0]}' if len(existing_orders) > 0 else 'getOrders: No Orders found')

        return jsonify(existing_orders)

    except Exception as e:
        logger.error(f'getOrders: error {e}', exc_info=True)
        pass


@app.route('/cancel_orders', methods=["POST"])
def cancel_orders():
    try:
        trading = get_betfair_client_from_flask_session(session)

        result_queue = queue.Queue()
        threads = []
        
        cancel_details = request.get_json('bet_id')
        bet_id = cancel_details['bet_id']

        logger.info(f'cancelOrder: Cancelling orders {cancel_details}')

        if bet_id == 'All':
            cancel_all_orders(trading, result_queue)
        else:
            bet_id_str = '' if bet_id == 'ALL' else f"AND o.bet_id = '{bet_id}'"

            existing_orders = query_sqlite(f"""
                                    SELECT 
                                    o.bet_id, 
                                    o.market_id,
                                    o.size_remaining
                                    FROM
                                    orders o
                                    WHERE o.status = 'EXECUTABLE'
                                        {bet_id_str}
                                    """)

            for order in existing_orders:

                logger.info(f'cancelOrder: Cancelling details {order}')

                market_id = order['market_id']
                bet_id = order['bet_id']
                sr = order['size_remaining']

                thread = Thread(target=cancel_order, args=(trading, bet_id, market_id, sr, result_queue))
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

        logger.info(f'cancelOrder: response = {response_str}')
    
    except Exception as e:
        logger.error(f'cancelOrder: error {e}', exc_info=True)
        response_str = 'Error in cancel order code. Check Logs'
        pass

    # Example: Process IDs (you can modify this function)
    return jsonify({"message": f"{response_str}"})




# Process orders
@app.route('/place_orders', methods=["POST"])
def place_orders():
    try:
        trading = get_betfair_client_from_flask_session(session)

        result_queue = queue.Queue()
        threads = []
        
        order_details = request.get_json('order_details')

        for order in order_details['order_details']:

            logger.info(f"placeOrder: {order_details['order_details'][order]}")

            market_id = order.split('-')[0]
            selection_id = order.split('-')[1]
            side = order.split('-')[2]
            hedge = order_details['order_details'][order]['hedge']
            if not hedge:
                price = float(order_details['order_details'][order]['price'])
                size = float(order_details['order_details'][order]['size'])
            else:
                side = 'LAY'
                price_dict = query_sqlite(f"SELECT price FROM price p WHERE key = '{market_id}-{selection_id}-LAY-3'")
                price = price_dict[0]['price']
                exposure = query_sqlite(f"SELECT sum(ABS(exposure)) AS size FROM selection_exposure WHERE market_id = '{market_id}'")
                size =  round(exposure[0]['size'] / price,2)
                logger.info(f"placeOrder: Hedge order details. seleciton_id: {selection_id}, side: {side} market_id: {market_id}, size: {size}, price: {price}, exp: {exposure}")
            thread = Thread(target=place_order, args=(trading, selection_id, side, market_id, size, price, result_queue))
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

        logger.info(f'placeOrder: response = {response_str}')
    
    except Exception as e:
        logger.error(f'placeOrder: error {e}', exc_info=True)
        response_str = 'Error in order code. Check Logs'
        pass

    # Example: Process IDs (you can modify this function)
    return jsonify({"message": f"{response_str}"})

@app.route('/stop_process', methods=['POST'])
def stop_process():

    logger.info(f'stopProcess: Publish to redis to stop price stream')
    redis_client.publish('event_control', json.dumps({'event_id':False}))  # Publish to Redis

    return "Process stopped"

@app.route('/start_process', methods=['POST'])
def start_process():   
    data = request.get_json()
    url = data.get('url')  # This is the URL sent from JavaScript
    event_id = url.split('/')[-1]

    username = session.get('username', 'No name found')
    app_key = session.get('app_key', 'No app key found')
    e = session.get('e', 'No e token found')

    # Publish event id for price streaming
    logger.info(f'startProcess: Publish {event_id} to redis for price stream')
    redis_client.publish('event_control', json.dumps({'username': username, 'app_key': app_key, 'e': e, 'context': context, 'event_id':event_id}))  # Publish to Redis

    return "Process started"

@app.route('/update_selection', methods=['POST'])
def update_selection():
    data = request.get_json()
    market_id = data.get('market_id')  # This is the URL sent from JavaScript
    add_remove = data.get('add_remove')  # This is the URL sent from JavaScript

    logger.info(f"updateSelection: {data}")

    with open('/data/selected_markets.pkl', 'rb') as f:
        my_list = pickle.load(f)
    
    if add_remove == 'add':
        my_list.append(str(market_id))
    elif add_remove == 'remove':
        my_list.remove(str(market_id))

    with open('/data/selected_markets.pkl', 'wb') as f:
        pickle.dump(my_list, f)

    return "Updated Selection"

@app.route('/cache_input', methods=['POST'])
def cache_input():
    data = request.get_json()
    key = data.get('key')
    value = data.get('value')
    session[key] = value

    logger.info(f"cacheInput: {data}")
    return jsonify(success=True)

# Run App
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
