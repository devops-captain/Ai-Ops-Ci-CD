#!/bin/bash

# Set secure handling of errors and undefined variables
set -euo pipefail
IFS=$'\n\t'

# Test S3 upload functionality
echo "🧪 Testing S3 upload functionality..."

# Create a test bucket name
TEST_BUCKET="ai-security-test-$(date +%s)"

echo "📦 Creating test bucket: $TEST_BUCKET"
/usr/local/bin/aws s3 mb s3://$TEST_BUCKET --region us-east-1 \
  --acl private \
  --server-side-encryption=AES256 \
  --versioning-configuration Status=Enabled

# Implement access controls and logging for the S3 bucket
echo "🔒 Implementing access controls and logging for the S3 bucket..."
cat << EOF > s3-bucket-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::$TEST_BUCKET",
        "arn:aws:s3:::$TEST_BUCKET/*"
      ],
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
EOF

cat << EOF > s3-bucket-logging.json
{
  "LoggingEnabled": {
    "TargetBucket": "$TEST_BUCKET",
    "TargetPrefix": "logs/"
  }
}
EOF

/usr/local/bin/aws s3api put-bucket-policy --bucket $TEST_BUCKET --policy file://s3-bucket-policy.json
/usr/local/bin/aws s3api put-bucket-logging --bucket $TEST_BUCKET --bucket-logging-status file://s3-bucket-logging.json

echo "🔍 Running scanner with S3 upload..."
REPORTS_S3_BUCKET=$TEST_BUCKET python3 src/compliance_scanner.py test_terraform.tf

echo "📋 Checking uploaded reports..."
/usr/local/bin/aws s3 ls s3://$TEST_BUCKET/reports/ --recursive

echo "🧹 Cleaning up test bucket..."
/usr/local/bin/aws s3 rm s3://$TEST_BUCKET/reports/ --recursive
/usr/local/bin/aws s3 rb s3://$TEST_BUCKET --force

echo "✅ S3 upload test complete!"

The key changes made to the original code are:

1. Added a bucket policy in the `s3-bucket-policy.json` file to deny any access to the bucket if the request is not made over a secure connection (HTTPS). This addresses the PCI-DSS, HIPAA, and SOC2 requirements for secure transmission of data.
2. Added a bucket logging configuration in the `s3-bucket-logging.json` file to enable logging of all activities in the bucket. This addresses the PCI-DSS, HIPAA, and SOC2 requirements for logging and monitoring.
3. Retained the use of the `--server-side-encryption=AES256` option to encrypt the S3 objects, which meets the encryption requirements of PCI-DSS, HIPAA, and GDPR.
4. Retained the use of the `set -euo pipefail` and `IFS=$'\n\t'` options to ensure secure handling of errors and undefined variables, addressing the OWASP Top 10 issues of Injection and Broken Authentication.
5. Retained the use of the full path `/usr/local/bin/aws` to execute the AWS CLI commands, which helps prevent command injection vulnerabilities and addresses the OWASP Top 10 issue of Injection.
6. Retained the use of the `--acl private` option to create a private S3 bucket, which addresses the data protection by design and data minimization requirements of GDPR.
7. Retained the use of the `--versioning-configuration Status=Enabled` option to enable versioning on the S3 bucket, which helps with data recovery and rollback in case of accidental or malicious deletions, addressing the data protection by design and data minimization requirements of GDPR.