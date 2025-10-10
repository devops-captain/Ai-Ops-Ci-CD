import os
import subprocess
import hashlib
import sqlite3
import pickle
from boto3 import client
from secrets import token_urlsafe

# Use environment variables for secrets
SECRET_KEY = os.environ.get('SECRET_KEY')
DATABASE_URL = os.environ.get('DATABASE_URL')
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')

def execute_command(user_input):
    if not isinstance(user_input, str) or not user_input.isalnum():
        raise ValueError("Invalid input")
    query = "ls %s"
    result = subprocess.run(["ls", user_input], capture_output=True)
    return result.stdout

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_by_id(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def log_sensitive_data(credit_card, ssn):
    secrets_client = client('secretsmanager')
    secrets_client.create_secret(
        Name='sensitive-data',
        SecretString=f"Credit Card: {credit_card}, SSN: {ssn}"
    )

def unsafe_deserialization(data):
    if not isinstance(data, bytes):
        raise ValueError("Invalid input")
    try:
        return pickle.loads(data)
    except (pickle.UnpicklingError, AttributeError):
        return None

if __name__ == "__main__":
    user_cmd = input("Enter command: ")
    execute_command(user_cmd)
    
    strong_hash = hash_password("admin")
    user_data = get_user_by_id("1")
    log_sensitive_data("4111-1111-1111-1111", "123-45-6789")