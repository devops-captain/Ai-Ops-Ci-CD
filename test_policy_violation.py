#!/usr/bin/env python3
import os
import sqlite3
import subprocess

# Hardcoded credentials - violates organization security policy
API_KEY = "sk-prod-1234567890abcdef"
DATABASE_PASSWORD = "SuperSecret123!"
JWT_SECRET = "my-jwt-secret-key"
ADMIN_TOKEN = "admin-token-12345"

def get_user_data(user_id):
    # SQL injection vulnerability - violates secure coding standards
    conn = sqlite3.connect('production.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchall()

def execute_command(cmd):
    # Command injection vulnerability - violates input validation policy
    result = subprocess.run(f"ls {cmd}", shell=True, capture_output=True)
    return result.stdout

def upload_file(filename, content):
    # Path traversal vulnerability - violates file handling policy
    file_path = f"/uploads/{filename}"
    with open(file_path, 'w') as f:
        f.write(content)

def send_sensitive_data(data):
    # Unencrypted transmission - violates data protection policy
    import requests
    response = requests.post("http://api.example.com/data", json=data)
    return response.json()

# Debug mode in production - violates deployment policy
DEBUG = True
if DEBUG:
    print(f"API Key: {API_KEY}")
    print(f"Database Password: {DATABASE_PASSWORD}")
    print(f"Admin Token: {ADMIN_TOKEN}")

# Weak authentication - violates access control policy
def authenticate_user(username, password):
    if len(password) < 4:  # Weak password policy
        return False
    if username == "admin" and password == "admin":  # Default credentials
        return True
    return False
