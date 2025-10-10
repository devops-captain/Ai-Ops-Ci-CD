import boto3
import json
import os
from datetime import datetime
from boto3.session import Session

def fix_manifest():
    secrets_client = boto3.client('secretsmanager')
    secret = secrets_client.get_secret_value(SecretId=os.environ.get('BUCKET_SECRET_ID'))
    bucket = secret['SecretString']

    s3 = boto3.client('s3', region_name='us-east-1')
    response = s3.list_objects_v2(Bucket=bucket, Prefix='reports/')
    reports = []

    for obj in response.get('Contents', []):
        if obj['Key'].endswith('.json'):
            reports.append({
                'key': obj['Key'],
                'timestamp': obj['LastModified']
            })

    reports.sort(key=lambda x: x['timestamp'], reverse=True)
    latest_reports = [r['key'] for r in reports[:10]]

    manifest = {"reports": latest_reports}

    s3.put_object(
        Bucket=bucket,
        Key='reports-manifest.json',
        Body=json.dumps(manifest, indent=2),
        ContentType='application/json',
        ServerSideEncryption='AES256'
    )

    print(f"✅ Fixed manifest with {len(latest_reports)} latest reports:")
    for report in latest_reports:
        print(f"  - {report}")

if __name__ == "__main__":
    fix_manifest()