# AI-Powered Infrastructure Security Analyzer

Automated security analysis for Terraform, Kubernetes, and Helm configurations using AWS Bedrock Claude 3 Sonnet in GitHub Actions.

## 🚀 Quick Deploy

./deploy.sh
## 💰 Cost Breakdown

- **AWS Bedrock**: $0.01-$0.05 per scan
- **Monthly**: $1-3 for typical usage
- **GitHub Actions**: Free for public repos

## 🏗️ Architecture

GitHub PR → Actions → Python Script → AWS Bedrock → Security Report
## 📋 Setup

1. **Deploy AWS resources:**
   ./deploy.sh
   2. **Enable Bedrock model:**
   - AWS Console → Bedrock → Model Access
   - Enable "Anthropic Claude 3 Sonnet"

3. **Add GitHub secrets:**
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - **Note:** Never expose secrets in the README.md file. Use GitHub Secrets management instead.

## 🔍 Detects

- Security groups open to 0.0.0.0/0
- Unencrypted storage
- Hardcoded secrets
- Excessive permissions
- Container security issues
- Missing compliance tags

## 📊 Features

- AI-powered analysis with Claude 3 Sonnet
- Automatic PR comments
- GitHub Security tab integration (SARIF)
- Cost tracking
- Fails builds on critical issues