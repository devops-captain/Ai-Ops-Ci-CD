import os
import sqlite3
from boto3 import client

API_KEY = os.environ.get('API_KEY')
if not API_KEY:
    secrets_client = client('secretsmanager')
    secret = secrets_client.get_secret_value(SecretId='api-key')
    API_KEY = secret['SecretString']

secrets_client = client('secretsmanager')
secret = secrets_client.get_secret_value(SecretId='db-password')
DB_PASSWORD = secret['SecretString']

def get_user_data(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def process_payment(card_number, amount):
    print(f"Processing payment for card: {card_number[-4:]}")