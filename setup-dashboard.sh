#!/bin/bash

# AI Security Scanner Dashboard Setup Script

set -e

# Configuration
BUCKET_NAME="ai-security-scanner-reports-$(date +%s)"
REGION="us-east-1"

echo "🚀 Setting up AI Security Scanner Dashboard..."

# Create S3 bucket for reports
echo "📦 Creating S3 bucket: $BUCKET_NAME"
aws s3 mb s3://$BUCKET_NAME --region $REGION

# Enable static website hosting with encryption
echo "🌐 Enabling static website hosting with encryption..."
aws s3 website s3://$BUCKET_NAME --index-document index.html --error-document error.html
aws s3api put-bucket-encryption --bucket $BUCKET_NAME --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Set bucket policy to deny public read access and allow only authorized users
echo "🔒 Setting bucket policy..."
cat > bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyPublicRead",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    },
    {
      "Sid": "AllowAuthorizedAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::123456789012:user/authorized_user1",
          "arn:aws:iam::123456789012:user/authorized_user2"
        ]
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://bucket-policy.json

# Update HTML with bucket name and region
echo "📝 Updating website configuration..."
sed "s/YOUR_REPORTS_BUCKET_NAME/$BUCKET_NAME/g" website/index.html > website/index-configured.html
sed -i.bak "s/us-east-1/$REGION/g" website/index-configured.html

# Upload website files with content type
echo "📤 Uploading website files..."
aws s3 cp website/index-configured.html s3://$BUCKET_NAME/index.html --content-type text/html
aws s3 cp website/error.html s3://$BUCKET_NAME/error.html --content-type text/html

# Get website URL
WEBSITE_URL="https://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"

# Enable logging and monitoring
echo "🔍 Enabling logging and monitoring..."
aws cloudtrail create-trail --name ai-security-scanner-dashboard-trail --s3-bucket-name $BUCKET_NAME --is-multi-region-trail --enable-log-file-validation
aws cloudwatch put-metric-alarm --alarm-name ai-security-scanner-dashboard-alarm --metric-name UnauthorizedAccess --namespace AWS/S3 --statistic Sum --period 300 --threshold 0 --comparison-operator GreaterThanOrEqualToThreshold --dimensions "Name=BucketName,Value=$BUCKET_NAME" "Name=FilterId,Value=EntireBucket" --evaluation-periods 1 --alarm-actions arn:aws:sns:$REGION:123456789012:security-alerts

echo "✅ Dashboard setup complete!"
echo ""
echo "📊 Dashboard URL: $WEBSITE_URL"
echo "📦 Reports Bucket: $BUCKET_NAME"
echo ""
echo "🔧 To use with scanner, set environment variable:"
echo "export REPORTS_S3_BUCKET=$BUCKET_NAME"
echo ""
echo "🧪 Test the scanner with S3 upload:"
echo "REPORTS_S3_BUCKET=$BUCKET_NAME python3 src/compliance_scanner.py test_terraform.tf"

# Clean up
rm -f bucket-policy.json website/index-configured.html website/index-configured.html.bak

echo ""
echo "🎉 Your AI Security Scanner Dashboard is ready!"
echo "Visit: $WEBSITE_URL"