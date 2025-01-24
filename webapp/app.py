from flask import Flask, render_template, Response, jsonify
from bf_api.list_events import list_events
from bf_api.list_market_catalogue import list_market_catalogue
# from bf_api.stream_price2 import list_market_catalogue
from celery import Celery
from flask_sse import sse
from threading import Thread
import redis
import json

app = Flask(__name__)
app.config["REDIS_URL"] = "redis://redis:6379"  # Update this if using a remote Redis server
app.register_blueprint(sse, url_prefix='/stream')

redis_client = redis.Redis(host='redis', port=6379)

def listen_to_redis():
    with app.app_context():
        pubsub = redis_client.pubsub()
        pubsub.subscribe('stream_price')

        for message in pubsub.listen():
            if message['type'] == 'message':
                data = message['data'].decode('utf-8')
                data = json.loads(data)
                print(data)
                sse.publish(data, type='update')
                print('data sent')

# Run the Redis listener in a background thread
Thread(target=listen_to_redis, daemon=True).start()

@app.route('/')
def home():
    events = list_events()
    return render_template('events.html', events=events)

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    # Find the event by name
    market_catalogue = list_market_catalogue(event_id)
    redis_client.publish('event_control', str(event_id))  # Publish to Redis
    return render_template('markets.html',  market_catalogue=market_catalogue, event_name=market_catalogue[0]['event'])

# @app.route('/task-stream/<task_id>')
# def task_stream(task_id):
#     def generate():
#         task = fetch_odds_task.AsyncResult(task_id)
#         while not task.ready():
#             yield f"data: {task.state}\n\n"
#             time.sleep(1)
#         yield f"data: {task.result}\n\n"

#     return Response(generate(), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')