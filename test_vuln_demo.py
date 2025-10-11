#!/usr/bin/env python3
import subprocess
import sqlite3
import pickle
import os

# Hardcoded credentials
API_KEY = "sk-1234567890abcdef"
DB_PASSWORD = "admin123"

def execute_command(user_input):
    # Command injection vulnerability
    result = subprocess.run(f"ls {user_input}", shell=True, capture_output=True)
    return result.stdout

def query_database(username):
    # SQL injection vulnerability
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()

def load_user_data(data):
    # Unsafe deserialization
    return pickle.loads(data)

def weak_crypto():
    # Weak cryptographic function
    import hashlib
    password = "secret123"
    return hashlib.md5(password.encode()).hexdigest()
