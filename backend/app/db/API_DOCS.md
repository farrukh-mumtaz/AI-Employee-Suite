# AI Employee Suite - Backend API Documentation

## Authentication Endpoints

### POST /auth/signup
Creates a new user account.
Body: `{ "name": str, "email": str, "password": str }`
Returns: user_id and success message.

### POST /auth/login
Logs in a user and returns tokens.
Body: `{ "email": str, "password": str }`
Returns: `access_token`, `refresh_token`, `token_type`.

### POST /auth/refresh
Gets a new access token using a refresh token.
Body: `{ "refresh_token": str }`
Returns: new `access_token`.

### GET /auth/admin-only
Test endpoint, only accessible by users with role "admin".
Requires: `Authorization: Bearer <access_token>` header.

## HR Endpoints

All HR endpoints require a valid access token in the `Authorization: Bearer <token>` header.

### POST /hr/employees
Creates a new employee record.
Body: `{ "name": str, "department": str, "position": str }`

### GET /hr/employees
Returns a list of all employees.

### GET /hr/employees/{employee_id}
Returns a single employee's details.

### POST /hr/leaves
Submits a new leave request. Status starts as "pending".
Body: `{ "employee_id": int, "start_date": datetime, "end_date": datetime, "reason": str }`

### GET /hr/leaves
Returns all leave requests.

### PATCH /hr/leaves/{leave_id}
Updates a leave request's status. Requires admin role.
Body: `{ "status": "approved" | "rejected" }`