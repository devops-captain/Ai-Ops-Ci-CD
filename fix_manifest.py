#!/usr/bin/env python3
import boto3
import json
from datetime import datetime

def fix_manifest():
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket = 'ai-security-scanner-reports-1759503117'
    
    # List all reports
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
    
    # Upload manifest
    s3.put_object(
        Bucket=bucket,
        Key='reports-manifest.json',
        Body=json.dumps(manifest, indent=2),
        ContentType='application/json'
    )
    
    print(f"✅ Fixed manifest with {len(latest_reports)} latest reports:")
    for report in latest_reports:
        print(f"  - {report}")

if __name__ == "__main__":
    fix_manifest()
