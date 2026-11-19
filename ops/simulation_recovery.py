"""Bounded recovery for the existing paper simulation; never changes trading rules."""
import base64
import datetime as dt
import json
import os
import urllib.request

REPO = 'ShimixTalk/Shimix-Soroban'
WORKFLOW = 'shimix-trading-simulation.yml'
WINDOW = dt.timedelta(minutes=45)
ACTIVE = {'queued', 'in_progress', 'waiting', 'pending', 'requested'}


def timestamp(value):
    result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone required')
    return result


def decide(state, runs, now):
    if now.tzinfo is None:
        raise ValueError('Timezone required')
    # Missing or ambiguous safety evidence must never dispatch a robot.
    if state.get('realTradingEnabled') is not False or state.get('exchangeApiConnected') is not False:
        return 'unsafe_or_unknown_mode'
    age = now - timestamp(state['updatedAt'])
    if age < dt.timedelta(0):
        return 'future_snapshot'
    if age <= WINDOW:
        return 'fresh_snapshot'
    for run in runs:
        if run.get('path') != '.github/workflows/' + WORKFLOW:
            raise ValueError('Unexpected workflow')
        if run.get('status') in ACTIVE:
            return 'already_active'
        # Includes failed and cancelled attempts: a failure must not create a retry storm.
        if now - timestamp(run['created_at']) <= WINDOW:
            return 'recent_attempt'
    return 'dispatch'


def api(path, method='GET', body=None):
    request = urllib.request.Request(
        'https://api.github.com/repos/' + REPO + '/' + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json'}, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
        return json.loads(data) if data else None


def main():
    file = api('contents/hub/trading/robot-state.json?ref=shimix-hub')
    state = json.loads(base64.b64decode(file['content']))
    runs = api('actions/workflows/' + WORKFLOW + '/runs?per_page=100')['workflow_runs']
    reason = decide(state, runs, dt.datetime.now(dt.timezone.utc))
    print(json.dumps({'decision': reason, 'snapshotAt': state.get('updatedAt')}))
    if reason == 'dispatch':
        api('actions/workflows/' + WORKFLOW + '/dispatches', 'POST', {'ref': 'main'})
        print('Existing fictitious simulation requested; execution and trades are not guaranteed.')


if __name__ == '__main__':
    main()
