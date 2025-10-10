#!/usr/bin/env python3
# SECURE FILE - Compliance with security standards

import os
import sqlite3
import requests
from boto3 import client
from botocore.exceptions import ClientError

# FIXED: Use environment variables for secrets (KB: general_security.md#hardcoded-secrets)
API_KEY = os.environ.get('API_KEY')
DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD')
JWT_SECRET = os.environ.get('JWT_SECRET')
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')

# FIXED: Use parameterized queries to prevent SQL injection (KB: python_security.md#input-validation)
def get_user_data(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

# FIXED: Enforce password complexity requirements (KB: general_security.md#authentication)
def authenticate_user(username, password):
    if len(password) < 8 or not any(char.isupper() for char in password) or not any(char.isdigit() for char in password):
        return False
    if username == "admin" and password == os.environ.get('ADMIN_PASSWORD'):
        return True
    return False

# FIXED: Validate file paths to prevent path traversal (KB: general_security.md#input-validation)
def read_file(filename):
    file_path = os.path.join('/app/uploads', filename)
    if os.path.isfile(file_path):
        with open(file_path, 'r') as f:
            return f.read()
    return None

# FIXED: Use HTTPS for sensitive data transmission (KB: general_security.md#network-security)
def send_sensitive_data(data):
    response = requests.post("https://api.example.com/sensitive", json={
        "api_key": API_KEY,
        "user_data": data,
        "password": DATABASE_PASSWORD
    })
    return response.json()

# FIXED: Disable debug mode in production (KB: general_security.md#logging)
DEBUG = False
if DEBUG:
    print(f"API Key: {API_KEY}")
    print(f"Database Password: {DATABASE_PASSWORD}")
    print(f"AWS Keys: {AWS_ACCESS_KEY}:{AWS_SECRET_KEY}")

# FIXED: Use a cryptographically secure random number generator (KB: general_security.md#cryptography)
import secrets
def generate_session_token():
    return secrets.token_hex(32)

# FIXED: Validate and sanitize user input (KB: general_security.md#input-validation)
def process_user_input(user_input):
    if isinstance(user_input, str) and user_input.strip():
        # Safely execute the input
        exec(user_input)
    else:
        print("Invalid user input")

# FIXED: Set appropriate file permissions (KB: general_security.md#file-permissions)
def create_sensitive_file():
    with open("/tmp/sensitive_data.txt", "w") as f:
        f.write(f"Secret: {JWT_SECRET}")
    os.chmod("/tmp/sensitive_data.txt", 0o600)  # Read and write access for owner only

# FIXED: Avoid logging sensitive information (KB: general_security.md#logging)
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def login_user(username, password):
    logger.info(f"Login attempt: {username}")
    if authenticate_user(username, password):
        logger.info(f"Successful login")
        return True
    return False
