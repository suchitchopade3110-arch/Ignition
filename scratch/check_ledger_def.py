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

def check_ledger_definition():
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        schema = res.json()
        definition = schema.get("definitions", {}).get("architecture_ledger", {})
        import json
        print(json.dumps(definition, indent=2))
    else:
        print(f"Failed: {res.status_code}")

if __name__ == "__main__":
    check_ledger_definition()
