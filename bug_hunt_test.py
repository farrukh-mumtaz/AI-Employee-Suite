import requests

# Comprehensive backend testing script - exercises edge cases across all
# endpoints to surface bugs before they reach users. Results are printed
# so they can be compiled into a bug report.

BASE_URL = "http://127.0.0.1:8000"
bugs_found = []

def check(description, condition, actual_result=""):
    status = "OK" if condition else "BUG FOUND"
    print(f"[{status}] {description} {f'-> {actual_result}' if actual_result else ''}")
    if not condition:
        bugs_found.append(f"{description} -> {actual_result}")

# --- Auth edge cases ---
print("\n=== AUTH TESTS ===")

# Duplicate signup
email = "bughunt_test@example.com"
requests.post(f"{BASE_URL}/auth/signup", json={"name": "Bug Hunt", "email": email, "password": "test1234"})
r = requests.post(f"{BASE_URL}/auth/signup", json={"name": "Bug Hunt", "email": email, "password": "test1234"})
check("Duplicate signup should be rejected (400)", r.status_code == 400, r.status_code)

# Login with wrong password
r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": "wrongpassword"})
check("Wrong password should be rejected (401)", r.status_code == 401, r.status_code)

# Login with non-existent email
r = requests.post(f"{BASE_URL}/auth/login", json={"email": "doesnotexist@example.com", "password": "test1234"})
check("Non-existent user login should be rejected (401)", r.status_code == 401, r.status_code)

# Empty password signup
r = requests.post(f"{BASE_URL}/auth/signup", json={"name": "Test", "email": "empty_pw@example.com", "password": ""})
check("Empty password signup - check if rejected or accepted", r.status_code in [400, 422], r.status_code)

# Get valid token for further tests
r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": "test1234"})
token = r.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# Refresh with garbage token
r = requests.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": "not.a.real.token"})
check("Garbage refresh token should be rejected (401)", r.status_code == 401, r.status_code)

# --- HR edge cases ---
print("\n=== HR TESTS ===")

# Get non-existent employee
r = requests.get(f"{BASE_URL}/hr/employees/999999", headers=headers)
check("Non-existent employee should return 404", r.status_code == 404, r.status_code)

# Create employee with empty name
r = requests.post(f"{BASE_URL}/hr/employees", headers=headers, json={"name": "", "department": "Eng", "position": "Dev"})
check("Empty employee name - check if rejected or accepted", r.status_code in [400, 422], r.status_code)

# Leave request for non-existent employee
r = requests.post(f"{BASE_URL}/hr/leaves", headers=headers, json={
    "employee_id": 999999, "start_date": "2026-08-10T00:00:00",
    "end_date": "2026-08-12T00:00:00", "reason": "Test"
})
check("Leave request for non-existent employee should return 404", r.status_code == 404, r.status_code)

# Update non-existent leave status
r = requests.patch(f"{BASE_URL}/hr/leaves/999999", headers=headers, json={"status": "approved"})
check("Updating non-existent leave should return 404 or 403 (if not admin)", r.status_code in [403, 404], r.status_code)

# No auth header on protected endpoint
r = requests.get(f"{BASE_URL}/hr/employees")
check("No auth header should return 401 or 403", r.status_code in [401, 403], r.status_code)

# --- Orchestration edge cases ---
print("\n=== ORCHESTRATION TESTS ===")

r = requests.post(f"{BASE_URL}/orchestrate/", headers=headers, json={
    "agent_name": "nonexistent_agent", "user_input": "test"
})
check("Unknown agent_name should return 400", r.status_code == 400, r.status_code)

r = requests.post(f"{BASE_URL}/orchestrate/", headers=headers, json={
    "agent_name": "hr", "user_input": ""
})
check("Empty user_input - check backend behavior", True, f"status={r.status_code}")

# --- Dashboard edge cases ---
print("\n=== DASHBOARD TESTS ===")

r = requests.get(f"{BASE_URL}/dashboard/metrics", headers=headers)
check("Non-admin accessing dashboard should return 403", r.status_code == 403, r.status_code)

# --- Summary ---
print("\n=== SUMMARY ===")
print(f"Total bugs found: {len(bugs_found)}")
for b in bugs_found:
    print(f"- {b}")