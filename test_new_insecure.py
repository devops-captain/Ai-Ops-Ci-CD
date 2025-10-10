#!/usr/bin/env python3

import os
import subprocess
import hashlib

# Hardcoded secrets
SECRET_KEY = "super_secret_key_123"
DATABASE_URL = "postgresql://admin:password123@localhost/mydb"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"

def execute_command(user_input):
    # Command injection vulnerability
    result = subprocess.run(f"ls {user_input}", shell=True, capture_output=True)
    return result.stdout

def hash_password(password):
    # Weak hashing algorithm
    return hashlib.md5(password.encode()).hexdigest()

def get_user_by_id(user_id):
    # SQL injection vulnerability
    import sqlite3
    conn = sqlite3.connect('users.db')
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    return conn.execute(query).fetchall()

def log_sensitive_data(credit_card, ssn):
    # Logging sensitive data in plain text
    with open('/tmp/sensitive.log', 'a') as f:
        f.write(f"Credit Card: {credit_card}, SSN: {ssn}\n")

def unsafe_deserialization(data):
    # Unsafe deserialization
    import pickle
    return pickle.loads(data)

if __name__ == "__main__":
    # Insecure usage
    user_cmd = input("Enter command: ")
    execute_command(user_cmd)
    
    weak_hash = hash_password("admin")
    user_data = get_user_by_id("1' OR '1'='1")
    log_sensitive_data("4111-1111-1111-1111", "123-45-6789")
