# Backend Bug Report

## Testing Method

Wrote a comprehensive test script (bug_hunt_test.py) that exercises edge cases across authentication, HR, orchestration, and dashboard endpoints - testing invalid inputs, missing data, non-existent records, and unauthorized access.

## Bugs Found & Fixed

### Bug 1: Empty password accepted during signup
- Endpoint: POST /auth/signup
- Issue: An empty string was accepted as a valid password, allowing accounts with no real password.
- Expected: Should return 400 Bad Request
- Actual (before fix): Returned 200 OK
- Fix: Added validation to reject empty/whitespace-only passwords.
- Status: Fixed and verified.

### Bug 2: Empty employee name accepted
- Endpoint: POST /hr/employees
- Issue: An employee record could be created with an empty name field.
- Expected: Should return 400 Bad Request
- Actual (before fix): Returned 200 OK
- Fix: Added validation to reject empty/whitespace-only employee names.
- Status: Fixed and verified.

## Other Cases Tested (No Bugs Found)

- Duplicate email signup - correctly rejected
- Wrong password login - correctly rejected
- Non-existent user login - correctly rejected
- Invalid/garbage refresh token - correctly rejected
- Fetching non-existent employee - correctly returns 404
- Leave request for non-existent employee - correctly returns 404
- Unauthorized access to protected endpoints - correctly returns 401/403
- Unknown agent name in orchestration - correctly returns 400
- Non-admin accessing dashboard - correctly returns 403

## Verification

Re-ran the full test suite after fixes: 0 bugs remaining (down from 2). Full regression suite (regression_test.py) also passes.