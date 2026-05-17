import os, json, base64, urllib.request, urllib.error

token = os.environ['GH_TOKEN']
repo  = os.environ['REPO']
branch = os.environ['BRANCH']

with open('results.json', 'rb') as f:
    content = base64.b64encode(f.read()).decode()

url = f'https://api.github.com/repos/{repo}/contents/results.json'
headers = {'Authorization': f'token {token}', 'Content-Type': 'application/json'}

# Get existing SHA if file already exists
sha = None
try:
    req = urllib.request.Request(f'{url}?ref={branch}', headers=headers)
    with urllib.request.urlopen(req) as r:
        sha = json.loads(r.read())['sha']
except urllib.error.HTTPError:
    pass

payload = {'message': 'chore: update flight search results', 'content': content, 'branch': branch}
if sha:
    payload['sha'] = sha

req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method='PUT')
try:
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
        print('Uploaded:', result['content']['name'])
except urllib.error.HTTPError as e:
    print('Error:', e.read().decode())
    raise
