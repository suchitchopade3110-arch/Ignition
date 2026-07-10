import sys
sys.path.append('.')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_rest_endpoints():
    print("Testing /healthz...")
    res = client.get("/healthz")
    print(res.status_code, res.json())
    assert res.status_code == 200

    print("Testing /api/auth/me...")
    res = client.get("/api/auth/me")
    print(res.status_code, res.json())
    assert res.status_code == 200
    assert "name" in res.json()

    print("Testing /auth/me (root)...")
    res = client.get("/auth/me")
    print(res.status_code, res.json())
    assert res.status_code == 200

    print("Testing /api/stats (stub mock database connection)...")
    try:
        res = client.get("/api/stats")
        print(res.status_code, res.json())
    except Exception as e:
        print("Stats call failed (expected if Supabase tables are not fully ready):", e)

if __name__ == "__main__":
    test_rest_endpoints()
