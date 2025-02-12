from flask import Flask, render_template, Response, jsonify, request
from bf_api.list_events import list_events
from bf_api.list_market_catalogue import list_market_catalogue
from bf_api.place_orders import place_order
# from bf_api.stream_price2 import list_market_catalogue
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

# setup logging
logging.basicConfig(level=logging.INFO)  # change to DEBUG to see log all updates
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["REDIS_URL"] = "redis://redis:6379"  # Update this if using a remote Redis server
app.register_blueprint(sse, url_prefix='/stream')

redis_client = redis.Redis(host='redis', port=6379)

# create trading instance (app key must be activated for streaming)
app_key = os.environ['BF_API_KEY']
username = os.environ['BF_USER']
password = os.environ['BF_PWD']
trading = betfairlightweight.APIClient(username, password, app_key=app_key, certs='/certs')

# Log in to Betfair API
trading.login()

def listen_to_redis():
    with app.app_context():
        pubsub = redis_client.pubsub()
        pubsub.subscribe('stream_price')

        data_cache = {}
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = message['data'].decode('utf-8')
                data = json.loads(data)

                market_id = data['market_id']
                selection_id = str(data['selection_id'])
                b_l = data['b_l']
                level = str(data['level'])
                price = data['price']
                size = data['size']
                updatetime = data['update_time']

                # Ensure market_id exists
                if market_id not in data_cache:
                    data_cache[market_id] = {}
                
                if selection_id not in data_cache[market_id]:
                    data_cache[market_id][selection_id] = {}
                
                if b_l not in data_cache[market_id][selection_id]:
                    data_cache[market_id][selection_id][b_l] = {}
                
                if level not in data_cache[market_id][selection_id][b_l]:
                    data_cache[market_id][selection_id][b_l][level] = {}
                
                data_cache[market_id][selection_id][b_l][level]['price'] = price
                data_cache[market_id][selection_id][b_l][level]['size'] = size
                data_cache[market_id][selection_id][b_l][level]['update_time'] = updatetime

                with open('./webapp/data_cache.pkl', 'wb') as file:
                    pickle.dump(data_cache, file)

                sse.publish(data, type='update')

# Run the Redis listener in a background thread
Thread(target=listen_to_redis, daemon=True).start()

@app.route('/')
def home():
    global trading
    events = list_events(trading)
    redis_client.publish('event_control', "Na")  # Publish to Redis

    return render_template('events.html', events=events)

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    global trading
    
    # Find the event by name
    market_catalogue = list_market_catalogue(trading, event_id)
    with open('./webapp/market_catalogue.pkl', 'wb') as file:
        pickle.dump(market_catalogue, file)

    market_catalogue_distinct_ids = []
    market_catalogue_distinct = []
    for m in market_catalogue:
        if m['market_id'] not in market_catalogue_distinct_ids:
            market_catalogue_distinct_ids.append(m['market_id'])
            market_catalogue_distinct.append({'id': m['market_id'], 'market_name': m['market_name']})

    redis_client.publish('event_control', str(event_id))  # Publish to Redis

    return render_template('markets2.html', markets=market_catalogue_distinct)

@app.route('/get-market', methods=["POST"])
def get_event_detail():
    selected_ids = request.json.get("selected_ids", [])
    # Find the event by name
    with open('./webapp/market_catalogue.pkl', 'rb') as file:
        market_catalogue = pickle.load(file)
    
    with open('./webapp/data_cache.pkl', 'rb') as file:
        data_cache = pickle.load(file)
    
    selected_markets = [d for d in market_catalogue if d['market_id'] in selected_ids]
    selected_markets2 = []
    updatetimelist = []
    for md in selected_markets:
        market_name = md['market_name']
        market_id = md['market_id']
        selection_name = md['selection_name']
        selection_id = str(md['selection_id'])
        try:
            back_level_2_price = data_cache[market_id][selection_id]['BACK']['2']['price'] if '2' in data_cache[market_id][selection_id]['BACK'] else 0
            back_level_1_price = data_cache[market_id][selection_id]['BACK']['1']['price'] if '1' in data_cache[market_id][selection_id]['BACK'] else 0
            back_level_0_price = data_cache[market_id][selection_id]['BACK']['0']['price'] if '0' in data_cache[market_id][selection_id]['BACK'] else 0
            lay_level_0_price = data_cache[market_id][selection_id]['LAY']['0']['price'] if '0' in data_cache[market_id][selection_id]['LAY'] else 0
            lay_level_1_price = data_cache[market_id][selection_id]['LAY']['1']['price'] if '1' in data_cache[market_id][selection_id]['LAY'] else 0
            lay_level_2_price = data_cache[market_id][selection_id]['LAY']['2']['price'] if '2' in data_cache[market_id][selection_id]['LAY'] else 0

            back_level_2_size = data_cache[market_id][selection_id]['BACK']['2']['size'] if '2' in data_cache[market_id][selection_id]['BACK'] else 0
            back_level_1_size = data_cache[market_id][selection_id]['BACK']['1']['size'] if '1' in data_cache[market_id][selection_id]['BACK'] else 0
            back_level_0_size = data_cache[market_id][selection_id]['BACK']['0']['size'] if '0' in data_cache[market_id][selection_id]['BACK'] else 0
            lay_level_0_size = data_cache[market_id][selection_id]['LAY']['0']['size'] if '0' in data_cache[market_id][selection_id]['LAY'] else 0
            lay_level_1_size = data_cache[market_id][selection_id]['LAY']['1']['size'] if '1' in data_cache[market_id][selection_id]['LAY'] else 0
            lay_level_2_size = data_cache[market_id][selection_id]['LAY']['2']['size'] if '2' in data_cache[market_id][selection_id]['LAY'] else 0

            back_level_2_updatetime = data_cache[market_id][selection_id]['BACK']['2']['update_time'] if '2' in data_cache[market_id][selection_id]['BACK'] else '0'
            back_level_1_updatetime = data_cache[market_id][selection_id]['BACK']['1']['update_time'] if '1' in data_cache[market_id][selection_id]['BACK'] else '0'
            back_level_0_updatetime = data_cache[market_id][selection_id]['BACK']['0']['update_time'] if '0' in data_cache[market_id][selection_id]['BACK'] else '0'
            lay_level_0_updatetime = data_cache[market_id][selection_id]['LAY']['0']['update_time'] if '0' in data_cache[market_id][selection_id]['LAY'] else '0'
            lay_level_1_updatetime = data_cache[market_id][selection_id]['LAY']['1']['update_time'] if '1' in data_cache[market_id][selection_id]['LAY'] else '0'
            lay_level_2_updatetime = data_cache[market_id][selection_id]['LAY']['2']['update_time'] if '2' in data_cache[market_id][selection_id]['LAY'] else '0'

            updatetimelist += [back_level_2_updatetime, back_level_1_updatetime, back_level_0_updatetime, lay_level_0_updatetime, lay_level_1_updatetime, lay_level_2_updatetime]
        except:
            back_level_2_price = 0
            back_level_1_price = 0
            back_level_0_price = 0
            lay_level_0_price = 0
            lay_level_1_price = 0
            lay_level_2_price = 0

            back_level_2_size = 0
            back_level_1_size = 0
            back_level_0_size = 0
            lay_level_0_size = 0
            lay_level_1_size = 0
            lay_level_2_size = 0

            back_level_2_updatetime = '0'
            back_level_1_updatetime = '0'
            back_level_0_updatetime = '0'
            lay_level_0_updatetime = '0'
            lay_level_1_updatetime = '0'
            lay_level_2_updatetime = '0'
            pass

        summary = {'market_name': market_name,
                   'market_id': market_id,
                   'selection_name': selection_name,
                   'selection_id': selection_id,
                   'back_level_2_price': back_level_2_price,
                   'back_level_1_price': back_level_1_price,
                   'back_level_0_price': back_level_0_price,
                   'lay_level_0_price': lay_level_0_price,
                   'lay_level_1_price': lay_level_1_price,
                   'lay_level_2_price': lay_level_2_price,
                   'back_level_2_size': back_level_2_size,
                   'back_level_1_size': back_level_1_size,
                   'back_level_0_size': back_level_0_size,
                   'lay_level_0_size': lay_level_0_size,
                   'lay_level_1_size': lay_level_1_size,
                   'lay_level_2_size': lay_level_2_size
                   }
        selected_markets2.append(summary)

    updatetime = max(updatetimelist) if len(updatetimelist) > 0 else ""
    selected_markets3 = {'update_time':updatetime, 'selected_markets': selected_markets2}
    return jsonify(selected_markets3)

@app.route('/process_blue_cells', methods=["POST"])
def process_blue_cells():
    global trading

    data = request.get_json()
    blue_cells = data.get('blue_cells', [])

    orderlist = [(cell[0].split('-')[0],cell[0].split('-')[1], cell[1].split('(')[0], 1,cell[0].split('-')[2]) for cell in blue_cells]

    response = place_order(trading, orderlist)
    response_str = "\n\n".join(response)

    # Example: Process IDs (you can modify this function)
    return jsonify({"message": f"{response_str}"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')