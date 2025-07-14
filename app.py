from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Setup MongoDB client
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/github_webhooks")
client = MongoClient(mongo_uri)
db = client.get_default_database()
events_collection = db.events

def parse_event(event_type, payload):
    if event_type == "push":
        return {
            "type": "PUSH",
            "author": payload.get("pusher", {}).get("name", "unknown"),
            "from_branch": None,
            "to_branch": payload.get("ref", "").split("/")[-1],
            "timestamp": datetime.utcnow()
        }

    elif event_type == "pull_request":
        pr = payload.get("pull_request", {})
        return {
            "type": "PULL_REQUEST",
            "author": pr.get("user", {}).get("login", "unknown"),
            "from_branch": pr.get("head", {}).get("ref", "unknown"),
            "to_branch": pr.get("base", {}).get("ref", "unknown"),
            "timestamp": datetime.utcnow()
        }

    elif event_type == "pull_request" and payload.get("action") == "closed" and payload["pull_request"].get("merged"):
        pr = payload["pull_request"]
        return {
            "type": "MERGE",
            "author": pr.get("user", {}).get("login", "unknown"),
            "from_branch": pr.get("head", {}).get("ref", "unknown"),
            "to_branch": pr.get("base", {}).get("ref", "unknown"),
            "timestamp": datetime.utcnow()
        }

    return None

@app.route('/')
def index():
    events = list(events_collection.find().sort("timestamp", -1).limit(20))

    for event in events:
        timestamp = event.get("timestamp")
        if isinstance(timestamp, datetime):
            readable_time = timestamp.strftime('%d %B %Y - %I:%M %p UTC').lstrip("0").replace(" 0", " ")
        else:
            readable_time = "Unknown time"

        event["readable_time"] = readable_time

    return render_template('index.html', events=events)

@app.route('/webhook', methods=['POST'])
def webhook():
    event_type = request.headers.get('X-GitHub-Event')
    payload = request.get_json()

    print(f"Received event: {event_type}")

    if event_type == 'ping':
        return jsonify({"message": "Ping received successfully"}), 200

    if not event_type or not payload:
        return jsonify({"error": "Missing event type or payload"}), 400

    formatted_event = parse_event(event_type, payload)

    if formatted_event:
        print("Storing event:", formatted_event)
        events_collection.insert_one(formatted_event)
        return jsonify({"message": "Event received and stored."}), 200

    return jsonify({"message": "Ignored event or unsupported event type."}), 204

@app.route('/events', methods=['GET'])
def get_events():
    events = list(events_collection.find().sort("timestamp", -1).limit(20))

    formatted_events = []
    for event in events:
        timestamp = event.get("timestamp")
        if isinstance(timestamp, datetime):
            readable_time = timestamp.strftime('%d %B %Y - %I:%M %p UTC').lstrip("0").replace(" 0", " ")
        else:
            readable_time = "Unknown time"

        formatted_events.append({
            "type": event.get("type", "UNKNOWN"),
            "author": event.get("author", "UNKNOWN"),
            "from_branch": event.get("from_branch", ""),
            "to_branch": event.get("to_branch", ""),
            "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else "N/A",
            "readable_time": readable_time
        })

    return jsonify(formatted_events)

@app.route('/health')
def health():
    try:
        server_info = client.server_info()
        return jsonify({"message": "MongoDB connected!", "version": server_info["version"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, port=port)
