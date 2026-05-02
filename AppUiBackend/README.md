# Flask Signup + Login + Dashboard + CRUD API Application

This project includes:
- Frontend: HTML templates + CSS
- Backend: Flask + SQLite + SQLAlchemy
- Authentication: Signup, Login, Logout, Session-based access control
- Dashboard redirect after login
- REST API methods: GET, POST, PUT, PATCH, DELETE

## Features

### Frontend
- Signup page
- Login page
- Dashboard page after successful login
- Registered user table

### Backend APIs
- `GET /api/users`
- `GET /api/users/<id>`
- `POST /api/users`
- `PUT /api/users/<id>`
- `PATCH /api/users/<id>`
- `DELETE /api/users/<id>`

## DELETE method usage
Use the DELETE method when a resource must be removed from the server permanently.
Example:
- Delete user account
- Delete order record
- Delete product entry

## Project Structure

```bash
app/
├── app.py
├── requirements.txt
├── README.md
├── static/
│   └── css/
│       └── style.css
└── templates/
    ├── base.html
    ├── login.html
    ├── signup.html
    ├── dashboard.html
    ├── 404.html
    └── 500.html
```

## How to run

### 1. Create virtual environment
```bash
python -m venv venv
```

### 2. Activate virtual environment
**Windows:**
```bash
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run application
```bash
python app.py
```

### 5. Open browser
```bash
http://127.0.0.1:5000
```

## Demo credentials
- Email: `admin@example.com`
- Password: `Admin@123`

## Sample API payloads

### POST /api/users
```json
{
  "full_name": "Krishna Das",
  "email": "krishna@example.com",
  "password": "Test@123",
  "role": "mentor",
  "is_active": true
}
```

### PUT /api/users/1
```json
{
  "full_name": "Admin Updated",
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true,
  "password": "Admin@123"
}
```

### PATCH /api/users/1
```json
{
  "role": "super_admin"
}
```
