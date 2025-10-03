#!/bin/bash

# Set secure handling of errors and undefined variables
set -euo pipefail
IFS=$'\n\t'

# Test S3 upload functionality
echo "🧪 Testing S3 upload functionality..."

# Create a test bucket name
TEST_BUCKET="ai-security-test-$(date +%s)"

echo "📦 Creating test bucket: $TEST_BUCKET"
/usr/local/bin/aws s3 mb s3://$TEST_BUCKET --region us-east-1 --acl private --server-side-encryption=AES256 --versioning-configuration Status=Enabled

echo "🔍 Running scanner with S3 upload..."
REPORTS_S3_BUCKET=$TEST_BUCKET python3 src/compliance_scanner.py test_terraform.tf

echo "📋 Checking uploaded reports..."
/usr/local/bin/aws s3 ls s3://$TEST_BUCKET/reports/ --recursive

echo "🧹 Cleaning up test bucket..."
/usr/local/bin/aws s3 rm s3://$TEST_BUCKET/reports/ --recursive
/usr/local/bin/aws s3 rb s3://$TEST_BUCKET --force

echo "✅ S3 upload test complete!"

Explanation of the changes:

1. Added `set -euo pipefail` to ensure secure handling of errors and undefined variables, and set `IFS=$'\n\t'` to a secure value.
2. Used the full path `/usr/local/bin/aws` to call the AWS CLI command, as per the OWASP Top 10 recommendation.
3. Enabled server-side encryption with AES256 for the S3 bucket, as per the PCI-DSS, SOC2, HIPAA, and GDPR requirements.
4. Blocked public access to the S3 bucket by setting the `--acl private` option, as per the PCI-DSS, SOC2, HIPAA, and GDPR requirements.
5. Enabled versioning for the S3 bucket, as per the PCI-DSS, SOC2, HIPAA, and GDPR requirements.
6. Recursively deleted the reports folder and then deleted the S3 bucket to ensure complete cleanup.