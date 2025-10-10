import os
import sqlite3
import secrets
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
    print(f"Processing payment for card: {card_number}")
    log_file = open("/tmp/payments.log", "a")
    log_file.write(f"Card: {card_number}, Amount: {amount}\n")
    log_file.close()

if __name__ == "__main__":
    user_data = get_user_data("1")
    process_payment("4111-1111-1111-1111-1111", 100.00)