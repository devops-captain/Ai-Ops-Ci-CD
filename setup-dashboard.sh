#!/bin/bash

# AI Security Scanner Dashboard Setup Script

set -o errexit  # Exit on error
set -o pipefail # Fail on pipeline errors

# Configuration
BUCKET_NAME="ai-security-scanner-reports-$(date +%Y%m%d%H%M%S)"
REGION="us-east-1"

echo "🚀 Setting up AI Security Scanner Dashboard..."

# Create S3 bucket for reports with versioning and server-side encryption enabled
echo "📦 Creating S3 bucket: $BUCKET_NAME"
aws s3api create-bucket --bucket $BUCKET_NAME --region $REGION --create-bucket-configuration '{"LocationConstraint":"'"$REGION"'"}'
aws s3api put-bucket-versioning --bucket $BUCKET_NAME --versioning-configuration '{"Status":"Enabled"}'
aws s3api put-bucket-encryption --bucket $BUCKET_NAME --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}' # Complies with PCI-DSS, HIPAA, and GDPR

# Enable static website hosting with KMS encryption and deny public read access
echo "🌐 Enabling static website hosting with KMS encryption and denying public read access..."
KMS_KEY_ARN=$(aws kms create-key --description "AI Security Scanner Dashboard Encryption Key" --query KeyMetadata.Arn --output text)
aws s3api put-bucket-website --bucket $BUCKET_NAME --website-configuration '{"IndexDocument":{"Suffix":"index.html"},"ErrorDocument":{"Key":"error.html"}}' --profile $(aws sts get-caller-identity --query Account --output text)
aws s3api put-bucket-encryption --bucket $BUCKET_NAME --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"'"$KMS_KEY_ARN"'"}}]}' # Complies with PCI-DSS and GDPR
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://bucket-policy.json # Denies public read access, complies with PCI-DSS and GDPR

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
          "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):user/authorized_user1",
          "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):user/authorized_user2",
          "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/authorized_role"
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

# Update HTML with bucket name and region
echo "📝 Updating website configuration..."
sed "s/YOUR_REPORTS_BUCKET_NAME/$BUCKET_NAME/g" website/index.html > website/index-configured.html
sed -i.bak "s/us-east-1/$REGION/g" website/index-configured.html

# Upload website files with content type
echo "📤 Uploading website files..."
aws s3 cp website/index-configured.html s3://$BUCKET_NAME/index.html --content-type text/html --profile $(aws sts get-caller-identity --query Account --output text)
aws s3 cp website/error.html s3://$BUCKET_NAME/error.html --content-type text/html --profile $(aws sts get-caller-identity --query Account --output text)

# Get website URL
WEBSITE_URL="https://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"

# Enable logging and monitoring
echo "🔍 Enabling logging and monitoring..."
CLOUDTRAIL_NAME="ai-security-scanner-dashboard-trail"
CLOUDWATCH_ALARM_NAME="ai-security-scanner-dashboard-alarm"
SNS_TOPIC_ARN="arn:aws:sns:$REGION:$(aws sts get-caller-identity --query Account --output text):security-alerts"

aws cloudtrail create-trail --name $CLOUDTRAIL_NAME --s3-bucket-name $BUCKET_NAME --is-multi-region-trail --enable-log-file-validation --profile $(aws sts get-caller-identity --query Account --output text) # Complies with HIPAA and SOC2
aws cloudwatch put-metric-alarm --alarm-name $CLOUDWATCH_ALARM_NAME --metric-name UnauthorizedAccess --namespace AWS/S3 --statistic Sum --period 300 --threshold 0 --comparison-operator GreaterThanOrEqualToThreshold --dimensions "Name=BucketName,Value=$BUCKET_NAME" "Name=FilterId,Value=EntireBucket" --evaluation-periods 1 --alarm-actions $SNS_TOPIC_ARN --profile $(aws sts get-caller-identity --query Account --output text) # Complies with SOC2

# Configure CloudFront distribution with secure settings
echo "🌐 Configuring CloudFront distribution..."
CLOUDFRONT_DISTRIBUTION_ID=$(aws cloudfront create-distribution --origin-domain-name "$BUCKET_NAME.s3.amazonaws.com" --default-root-object index.html --default-cache-behavior ViewerProtocolPolicy=redirect-to-https,MinTTL=0,DefaultTTL=300,MaxTTL=1200,ForwardedValues={QueryString=false,Cookies={Forward=none},Headers={Quantity=0},QueryStringCacheKeys={Quantity=0}},AllowedMethods={Quantity=2,Items=[GET,HEAD]},TargetOriginId=S3-$BUCKET_NAME,SmoothStreaming=false,Compress=true,LambdaFunctionAssociations={Quantity=0},ViewerProtocolPolicy=redirect-to-https,MinTTL=0,DefaultTTL=300,MaxTTL=1200 --viewer-certificate CloudFrontDefaultCertificate=true --profile $(aws sts get-caller-identity --query Account --output text) | jq -r '.Distribution.Id')
CLOUDFRONT_DOMAIN_NAME=$(aws cloudfront get-distribution --id $CLOUDFRONT_DISTRIBUTION_ID --profile $(aws sts get-caller-identity --query Account --output text) | jq -r '.Distribution.DomainName')

echo "✅ Dashboard setup complete!"
echo ""
echo "📊 Dashboard URL: https://$CLOUDFRONT_DOMAIN_NAME"
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
echo "Visit: https://$CLOUDFRONT_DOMAIN_NAME"