import requests

# Regression test: re-checks that previously working functionality
# still works correctly after today's changes.

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200, "Health check failed"
    print("PASS: /health")

def test_signup_and_login():
    email = "regression_test2@example.com"
    requests.post(f"{BASE_URL}/auth/signup", json={
        "name": "Regression Test", "email": email, "password": "test1234"
    })
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": "test1234"})
    assert r.status_code == 200, "Login failed"
    assert "access_token" in r.json(), "No access_token returned"
    print("PASS: signup + login")
    return r.json()["access_token"]

def test_leave_date_validation(token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BASE_URL}/hr/leaves", headers=headers, json={
        "employee_id": 1,
        "start_date": "2026-08-10T00:00:00",
        "end_date": "2026-08-05T00:00:00",
        "reason": "Testing bug fix"
    })
    print(f"Status code received: {r.status_code}, response: {r.json()}")
    assert r.status_code == 400, "Bug fix for date validation did not work"
    print("PASS: leave date validation bug fix")

def test_dashboard_metrics(token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/dashboard/metrics", headers=headers)
    print(f"Dashboard metrics status (expected 403 for non-admin): {r.status_code}")

if __name__ == "__main__":
    test_health()
    token = test_signup_and_login()
    test_leave_date_validation(token)
    test_dashboard_metrics(token)
    print("\nAll regression tests completed.")