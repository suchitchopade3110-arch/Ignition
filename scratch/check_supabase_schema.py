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

def check_schema():
    print(f"Fetching schema from {url}...")
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        schema = res.json()
        print("Definitions (Tables/Views):")
        for k in schema.get("definitions", {}).keys():
            print(f" - {k}")
        print("\nPaths (Endpoints):")
        for p in schema.get("paths", {}).keys():
            print(f" - {p}")
    else:
        print(f"Failed to fetch schema: {res.status_code} - {res.text}")

if __name__ == "__main__":
    check_schema()
