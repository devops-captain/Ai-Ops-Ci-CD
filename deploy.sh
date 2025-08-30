#!/bin/bash
set -e

echo "🚀 Deploying Infrastructure Security Analyzer"
echo "============================================="

# Check prerequisites
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not found. Install from: https://terraform.io"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Install from: https://aws.amazon.com/cli/"
    exit 1
fi

# Deploy infrastructure
cd infrastructure
echo "📦 Initializing Terraform..."
terraform init

echo "📋 Planning deployment..."
terraform plan

echo "🏗️ Deploying AWS resources..."
terraform apply -auto-approve

echo "🔑 Getting AWS credentials for GitHub..."
AWS_ACCESS_KEY=$(terraform output -raw aws_access_key_id)

cd ..

echo ""
echo "✅ Deployment Complete!"
echo "======================="
echo ""
echo "📋 Next Steps:"
echo "1. Add these secrets to your GitHub repository:"
echo "   - AWS_ACCESS_KEY_ID: $AWS_ACCESS_KEY"
echo "   - AWS_SECRET_ACCESS_KEY: [check terraform output]"
echo ""
echo "💰 Cost Breakdown (Monthly Estimates):"
echo "======================================="
echo "AWS Bedrock Claude 3 Sonnet:"
echo "  - Per scan: ~\$0.01 - \$0.05"
echo "  - Daily scans: ~\$0.30 - \$1.50/month"
echo ""
echo "💡 Total Estimated Cost: \$1-3/month"
echo ""
echo "🔧 Enable Bedrock Model Access:"
echo "1. Go to AWS Console > Bedrock > Model Access"
echo "2. Enable 'Anthropic Claude 3 Sonnet'"
echo ""
echo "🔐 Run this to see GitHub secrets:"
echo "cd infrastructure && terraform output setup_instructions"
