#!/usr/bin/env python3
import os
import sqlite3

# Hardcoded credentials - security violation
API_KEY = "sk-1234567890abcdef"
DATABASE_PASSWORD = "admin123"
JWT_SECRET = "mysecretkey"

def get_user_data(user_id):
    # SQL injection vulnerability
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchall()

def authenticate_user(username, password):
    # Weak password validation
    if len(password) < 4:
        return False
    return True

def upload_file(filename, content):
    # Path traversal vulnerability
    file_path = f"/uploads/{filename}"
    with open(file_path, 'w') as f:
        f.write(content)

def send_data(data):
    # Unencrypted HTTP transmission
    import requests
    response = requests.post("http://api.example.com/data", json=data)
    return response.json()

# Debug mode enabled in production
DEBUG = True
if DEBUG:
    print(f"API Key: {API_KEY}")
    print(f"Database Password: {DATABASE_PASSWORD}")
