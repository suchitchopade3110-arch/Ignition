import sys
sys.path.append('.')
import requests
from app.config import get_settings

settings = get_settings()
url = f"{settings.supabase_url}/rest/v1/"
headers = {
    "apikey": settings.supabase_key,
    "Authorization": f"Bearer {settings.supabase_key}"
}

def check_rpc():
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        schema = res.json()
        path_info = schema.get("paths", {}).get("/rpc/rls_auto_enable", {})
        print("rls_auto_enable path info:")
        import json
        print(json.dumps(path_info, indent=2))
    else:
        print(f"Failed: {res.status_code}")

if __name__ == "__main__":
    check_rpc()
