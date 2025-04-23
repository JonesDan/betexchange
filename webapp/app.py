from flask import Flask, render_template, jsonify, request, session, flash,redirect, url_for
from flask_session import Session
from flask_sse import sse
from threading import Thread
import redis
import os
import betfairlightweight
from utils import init_logger, place_order, list_market_catalogue, list_events
from utils_db import query_sqlite, init_db, delete_sample_files, init_selected_markets
import shelve
import queue
from cryptography.fernet import Fernet
from stream_price import stream_price
from stream_orders import stream_orders
import multiprocessing
import pickle
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
current_process = {'process_price': None, 'process_order': None}

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
            logger.info(f'Login: Successful Login')

            key = Fernet.generate_key()
            cipher = Fernet(key)
            encrypted_password = cipher.encrypt(password.encode())
            session['e'] = encrypted_password

            with open('/data/e.key', "wb") as file:
                file.write(key)

            results = delete_sample_files()
            logger.info(f'Login: Delete sample files output {results}')

            return redirect(url_for("eventList"))
        
        except Exception as e:
            logger.error(f'Login: error {e}')
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

        logger.info(f'EventList: Pulled {len(events)}')

        return render_template('eventList.html', events=events)
      
    except Exception as e:
        logger.error(f'EventList: error {e}')
        flash(f"Error pulling EventList: {e}", "danger")
        return redirect(url_for("login"))


@app.route('/eventDetail/<int:event_id>')
def eventDetail(event_id):
    try:
        logger.info(f'EventDetail: Pull event detail for {event_id}')

        logger.info(f'EventDetail: Create sqlite tables')
        results = init_db()
        logger.info(f'EventDetail: init_db results {results}')

        logger.info(f'EventDetail: Clear selected_markets shelve')
        init_selected_markets()

        logger.info(f'EventDetail: Pull event detail for {event_id}')

        # Get Sessions details
        username = session.get('username', 'No name found')
        app_key = session.get('app_key', 'No app key found')
        session_token = session.get('session_token', 'No session token found')
        
        trading = betfairlightweight.APIClient(username, 'test', app_key=app_key, certs='/certs')
        trading.session_token = session_token  # Restore session token

        logger.info(f'EventDetail: Pull Markets')

        # Get markets and build market cache
        list_market_catalogue(trading, event_id)
        market_ids_list = query_sqlite("SELECT DISTINCT event, market_id, market_name, printf('%.2f', total_matched) AS total_matched FROM market_catalogue")
        logger.info(market_ids_list)

        event_name =  market_ids_list[0]['event']

        logger.info(f'EventDetail: Pulled {len(market_ids_list)} Markets')

        return render_template('eventDetail.html', markets=market_ids_list, event_name=event_name)
    
    except Exception as e:
        logger.error(f'Eventdetail: error {e}')
        flash(f"Error pulling EventDetail: {e}", "danger")
        return redirect(url_for("login"))


@app.route('/get_prices', methods=["POST"])
def get_prices():

    try:
        market_id = request.json.get("marketid", [])

        logger.info(f'getPrices: Pull prices for {market_id}')

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
                                SUM(s.exposure) AS exposure
                            FROM price p
                            JOIN market_catalogue m
                                ON p.market_id = m.market_id AND p.selection_id = m.selection_id
                            LEFT JOIN selection_exposure s
                                ON m.market_id = s.market_id  AND m.selection_id = s.selection_id
                            WHERE p.market_id = '{market_id}'
                            GROUP BY p.market_id, m.market_name, p.selection_id, m.selection_name, p.side
                            """)
        
        
        logger.info(f'getPrices: Convert Prices and Size to List: {prices[0]}')

        for price in prices:
            price['priceList'] = price['priceList'].split(',')
            price['sizeList'] = price['sizeList'].split(',')
    
        return jsonify({'selected_markets': prices, 'update_time': price[0]['publish_time']})
    
    except Exception as e:
        logger.error(f'getPrices: error {e}')
        pass


# Process orders
@app.route('/place_orders', methods=["POST"])
def place_orders():
    try:
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

        for order in order_details['order_details']:

            logger.info(f"placeOrder: {order_details['order_details'][order]}")

            market_id = order.split('-')[0]
            selection_id = order.split('-')[1]
            b_l = order.split('-')[2]
            hedge = order_details['order_details'][order]['hedge']
            if not hedge:
                b_l2 = 'BACK' if b_l == 'batb' else 'LAY' if b_l == 'batl' else ''
                price = float(order_details['order_details'][order]['price'])
                size = float(order_details['order_details'][order]['size'])
                sizeMin = float(order_details['order_details'][order]['sizeMin'])
            else:
                b_l2 = 'LAY'
                price = query_sqlite(f"SELECT price FROM price p WHERE key = '{market_id}-{selection_id}-batl-0'")
                size = query_sqlite(f"SELECT exposure FROM selection_exposure p WHERE key = '{market_id}-{selection_id}'")
                sizeMin = 0
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

        logger.info(f'placeOrder: response = {response_str}')
    
    except Exception as e:
        logger.error(f'placeOrder: error {e}')
        response_str = 'Error in order code. Check Logs'
        pass

    # Example: Process IDs (you can modify this function)
    return jsonify({"message": f"{response_str}"})

@app.route('/stop_process', methods=['POST'])
def stop_process():
    global current_process

    # Stop existing process if it's running
    if current_process['process_price'] is not None and current_process['process_price'].is_alive():
        logger.info("stopProcess: 🛑 Stopping existing price process...")
        current_process['process_price'].terminate()
        current_process['process_price'].join()
        current_process['process_price'] = None

    if current_process['process_order'] is not None and current_process['process_order'].is_alive():
        logger.info("stopProcess:🛑 Stopping existing order process...")
        current_process['process_order'].terminate()
        current_process['process_order'].join()
        current_process['process_order'] = None

    return "Process stopped"

@app.route('/start_process', methods=['POST'])
def start_process():
    global current_process
    
    data = request.get_json()
    url = data.get('url')  # This is the URL sent from JavaScript
    event_id = url.split('/')[-1]

    username = session.get('username', 'No name found')
    app_key = session.get('app_key', 'No app key found')
    e = session.get('e', 'No e token found')


    # Stop existing process if it's running
    if current_process['process_price'] is not None and current_process['process_price'].is_alive():
        logger.info("startProcess: 🛑 Stopping existing price process...")
        current_process['process_price'].terminate()
        current_process['process_price'].join()

    if current_process['process_order'] is not None and current_process['process_order'].is_alive():
        logger.info("startProcess: 🛑 Stopping existin order process...")
        current_process['process_order'].terminate()
        current_process['process_order'].join()

    # Start new process
    new_proc_price = multiprocessing.Process(target=stream_price, args=(username, app_key, e, context, event_id))
    new_proc_price.start()
    current_process['process_price'] = new_proc_price
    logger.info("startProcess: ✅ Started new price background process.")
    # Start new process
    # new_proc_order = multiprocessing.Process(target=stream_orders, args=(username, app_key, e,  context))
    # new_proc_order.start()
    # current_process['process_order'] = new_proc_order
    # logger.info("startProcess: ✅ Started new order background process.")

    return "Process started"

@app.route('/update_selection', methods=['POST'])
def update_selection():
    data = request.get_json()
    market_id = data.get('market_id')  # This is the URL sent from JavaScript
    add_remove = data.get('add_remove')  # This is the URL sent from JavaScript

    logger.info(f"updateSelection: {data}")

    with open('data/selected_markets.pkl', 'rb') as f:
        my_list = pickle.load(f)
    
    if add_remove == 'add':
        my_list.append(str(market_id))
    elif add_remove == 'remove':
        my_list.remove(str(market_id))

    with open('data/selected_markets.pkl', 'wb') as f:
        pickle.dump(my_list, f)

    return "Updated Selection"
    

# Run App
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')