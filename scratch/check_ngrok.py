import urllib.request, json
import base64

data = json.loads(urllib.request.urlopen('http://127.0.0.1:4040/api/requests/http').read())
r = data['requests'][0]
print("Status:", r['response']['status_code'])
body_raw = r['response'].get('raw', '')
if body_raw:
    print("Raw body:", base64.b64decode(body_raw).decode('utf-8'))
else:
    print("Response JSON:", r['response'])
