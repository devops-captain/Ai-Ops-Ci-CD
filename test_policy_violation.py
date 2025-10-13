import os
import sqlite3
import subprocess
from boto3 import client

# Use environment variables or AWS Secrets Manager for secrets
api_key = os.environ.get('API_KEY')
secrets_client = client('secretsmanager')
db_password_secret = secrets_client.get_secret_value(SecretId='db-password')
db_password = db_password_secret['SecretString']
jwt_secret = os.environ.get('JWT_SECRET')
admin_token = os.environ.get('ADMIN_TOKEN')

def get_user_data(user_id):
    conn = sqlite3.connect('production.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def execute_command(cmd):
    if isinstance(cmd, str) and cmd.isalnum():
        result = subprocess.run(["ls", cmd], capture_output=True)
        return result.stdout
    else:
        return b"Invalid command"

def upload_file(filename, content):
    file_path = os.path.join("/uploads", os.path.basename(filename))
    with open(file_path, 'w') as f:
        f.write(content)

def send_sensitive_data(data):
    import requests
    response = requests.post("https://api.example.com/data", json=data)
    return response.json()

DEBUG = False

def authenticate_user(username, password):
    if len(password) >= 8 and any(char.isdigit() for char in password) and any(char.isupper() for char in password) and any(char.islower() for char in password):
        if username == "admin" and password == os.environ.get('ADMIN_PASSWORD'):
            return True
    return False