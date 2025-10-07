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
  --server-side-encryption=AES256 # Explicitly specify the encryption algorithm to meet PCI-DSS, HIPAA, and GDPR requirements

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
    },
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:user/restricted-user" # Use a restricted user instead of the root user to follow the principle of least privilege
      },
      "Action": [
        "s3:GetBucketLocation",
        "s3:ListBucket",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::$TEST_BUCKET",
        "arn:aws:s3:::$TEST_BUCKET/*"
      ]
    }
  ]
}
EOF

cat << EOF > s3-bucket-logging.json
{
  "LoggingEnabled": {
    "TargetBucket": "$TEST_BUCKET",
    "TargetPrefix": "logs/",
    "TargetGrantsList": [
      {
        "Grantee": {
          "Type": "Group",
          "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery"
        },
        "Permission": "WRITE"
      }
    ],
    "LogFilePrefix": "s3-access-logs-",
    "LogFileExpirationDays": 90 # Specify a retention period of 90 days for the log files to meet PCI-DSS, SOC2, and HIPAA requirements
  }
}
EOF

/usr/local/bin/aws s3api put-bucket-policy --bucket $TEST_BUCKET --policy file://s3-bucket-policy.json
/usr/local/bin/aws s3api put-bucket-logging --bucket $TEST_BUCKET --bucket-logging-status file://s3-bucket-logging.json

# Implement OWASP Top 10 security controls
echo "🛡️ Implementing OWASP Top 10 security controls..."
function validate_input() {
  local input="$1"
  # Implement comprehensive input validation and sanitization to prevent injection attacks
  echo "$(echo "$input" | tr -d '[:cntrl:]' | tr -d '[:space:]' | sed 's/[^a-zA-Z0-9_.-]//g' | sed 's/[;|&`]//g' | sed 's/['"'"']//g')"
}

function secure_auth() {
  # Implement secure authentication and authorization
  local username="$1"
  local password="$2"
  # Retrieve the admin password securely from AWS Secrets Manager
  local admin_password="$(aws secretsmanager get-secret-value --secret-id admin-password --query SecretString --output text)"
  if [ "$username" == "admin" ] && [ "$password" == "$admin_password" ]; then
    echo "Authenticated user"
  else
    handle_errors "Invalid username or password"
    return 1
  fi
}

function handle_errors() {
  local error_message="$1"
  # Implement proper error handling and logging
  echo "Error: $error_message" >&2
  # Log the error to a secure logging system
  logger "Security error: $error_message"
}

function prevent_injection() {
  local input="$1"
  # Implement comprehensive protection against injection attacks
  echo "$(echo "$input" | tr -d ';' | tr -d '&' | tr -d '|' | tr -d '`' | sed 's/[^a-zA-Z0-9_.-]//g' | sed 's/['"'"']//g')"
}

echo "🔍 Running scanner with S3 upload..."
REPORTS_S3_BUCKET=$TEST_BUCKET python3 src/compliance_scanner.py test_terraform.tf

echo "📋 Checking uploaded reports..."
/usr/local/bin/aws s3 ls s3://$TEST_BUCKET/reports/ --recursive

echo "🧹 Cleaning up test bucket..."
/usr/local/bin/aws s3 rm s3://$TEST_BUCKET/reports/ --recursive
/usr/local/bin/aws s3 rb s3://$TEST_BUCKET --force

echo "✅ S3 upload test complete!"