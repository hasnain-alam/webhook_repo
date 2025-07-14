from datetime import datetime

def parse_event(event_type, payload):
    if event_type == 'push':
        return {
            "type": "PUSH",
            "author": payload['pusher']['name'],
            "to_branch": payload['ref'].split('/')[-1],
            "timestamp": datetime.utcnow()
        }

    elif event_type == 'pull_request':
        return {
            "type": "PULL_REQUEST",
            "author": payload['pull_request']['user']['login'],
            "from_branch": payload['pull_request']['head']['ref'],
            "to_branch": payload['pull_request']['base']['ref'],
            "timestamp": datetime.utcnow()
        }

    elif event_type == 'pull_request' and payload.get('action') == 'closed' and payload['pull_request'].get('merged'):
        return {
            "type": "MERGE",
            "author": payload['pull_request']['user']['login'],
            "from_branch": payload['pull_request']['head']['ref'],
            "to_branch": payload['pull_request']['base']['ref'],
            "timestamp": datetime.utcnow()
        }

    return None
