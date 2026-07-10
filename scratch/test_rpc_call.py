import sys
sys.path.append('.')
from app.database import get_supabase

supabase = get_supabase()

def test_rpc():
    try:
        # Try calling with empty dictionary
        res = supabase.rpc("rls_auto_enable", {}).execute()
        print("Success:", res)
    except Exception as e:
        print("Failed:", e)

if __name__ == "__main__":
    test_rpc()
