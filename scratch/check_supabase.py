import sys
sys.path.append('.')
from app.database import get_supabase

supabase = get_supabase()

def test_queries():
    print("Connecting to Supabase...")
    tables = ["architecture_ledger", "reviews", "repos", "repository_settings", "settings"]
    for t in tables:
        try:
            res = supabase.table(t).select("*").limit(1).execute()
            print(f"Table '{t}' exists. Rows: {len(res.data)}")
        except Exception as e:
            print(f"Table '{t}' query failed: {e}")

if __name__ == "__main__":
    test_queries()
