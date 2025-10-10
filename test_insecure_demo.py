#!/usr/bin/env python3
# INSECURE FILE - Multiple security violations for testing

import os
import sqlite3
import requests

# VIOLATION 1: Hardcoded secrets (KB rule: general_security.md)
API_KEY = "sk-1234567890abcdef"
DATABASE_PASSWORD = "admin123"
JWT_SECRET = "mysecretkey"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# VIOLATION 2: SQL injection vulnerability
def get_user_data(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Direct string formatting - SQL injection risk
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchall()

# VIOLATION 3: Weak authentication
def authenticate_user(username, password):
    # No password complexity requirements
    if len(password) < 3:
        return False
    # Hardcoded admin credentials
    if username == "admin" and password == "password123":
        return True
    return False

# VIOLATION 4: Path traversal vulnerability
def read_file(filename):
    # No path validation
    file_path = f"/app/uploads/{filename}"
    with open(file_path, 'r') as f:
        return f.read()

# VIOLATION 5: Unencrypted HTTP transmission
def send_sensitive_data(data):
    # Using HTTP instead of HTTPS
    response = requests.post("http://api.example.com/sensitive", json={
        "api_key": API_KEY,
        "user_data": data,
        "password": DATABASE_PASSWORD
    })
    return response.json()

# VIOLATION 6: Debug mode in production
DEBUG = True
if DEBUG:
    print(f"API Key: {API_KEY}")
    print(f"Database Password: {DATABASE_PASSWORD}")
    print(f"AWS Keys: {AWS_ACCESS_KEY}:{AWS_SECRET_KEY}")

# VIOLATION 7: Insecure random number generation
import random
def generate_session_token():
    # Using weak random for security tokens
    return str(random.randint(100000, 999999))

# VIOLATION 8: No input validation
def process_user_input(user_input):
    # Direct execution without validation
    exec(user_input)

# VIOLATION 9: Insecure file permissions
def create_sensitive_file():
    with open("/tmp/sensitive_data.txt", "w") as f:
        f.write(f"Secret: {JWT_SECRET}")
    # File created with default permissions (readable by others)

# VIOLATION 10: Logging sensitive information
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def login_user(username, password):
    logger.info(f"Login attempt: {username}:{password}")  # Password in logs!
    if authenticate_user(username, password):
        logger.info(f"Successful login with API key: {API_KEY}")  # API key in logs!
        return True
    return False
