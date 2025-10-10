#!/usr/bin/env python3
import boto3
import json
import os
from datetime import datetime
from boto3.session import Session

def fix_manifest():
    # Use AWS Secrets Manager to retrieve the S3 bucket name
    secrets_client = boto3.client('secretsmanager')
    secret = secrets_client.get_secret_value(SecretId='s3-bucket-name')
    bucket = secret['SecretString']

    # List all reports
    s3 = boto3.client('s3', region_name='us-east-1')
    response = s3.list_objects_v2(Bucket=bucket, Prefix='reports/')
    reports = []

    for obj in response.get('Contents', []):
        if obj['Key'].endswith('.json'):
            reports.append({
                'key': obj['Key'],
                'timestamp': obj['LastModified']
            })

    # Sort by timestamp (newest first) and get latest 10
    reports.sort(key=lambda x: x['timestamp'], reverse=True)
    latest_reports = [r['key'] for r in reports[:10]]

    # Create manifest
    manifest = {"reports": latest_reports}

    # Upload manifest with server-side encryption
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

Compliance fixes:

1. **Hardcoded S3 bucket name (CWE-798: Use of Hard-coded Credentials)**: The S3 bucket name is now retrieved from AWS Secrets Manager, as per the "Secrets Management" section in the Knowledge Base.

2. **PCI-DSS, SOC2, HIPAA, GDPR, OWASP**: The code now uses server-side encryption (AES256) when uploading the manifest file to S3, as per the "S3 Bucket Security" section in the Knowledge Base.

No other compliance issues were found in the provided code based on the Knowledge Base context.