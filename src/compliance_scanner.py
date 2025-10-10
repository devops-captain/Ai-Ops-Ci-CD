import os
from boto3 import client

# Bad api_key = "sk-1234567890abcdef"
api_key = os.environ.get('API_KEY')
# Or use AWS Secrets Manager
secrets_client = client('secretsmanager')
secret = secrets_client.get_secret_value(SecretId='api-key')
api_key = secret['SecretString']

# Bad query = f"SELECT * FROM users WHERE id = {user_id}"
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))