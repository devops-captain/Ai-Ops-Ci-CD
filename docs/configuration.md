# ⚙️ Configuration Guide

## Environment Variables

All configuration is handled through environment variables to ensure zero hardcoded values and maximum flexibility.

### Required Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `AWS_REGION` | AWS region for Bedrock services | `us-east-1` | `us-west-2` |
| `BEDROCK_KB_ID` | Knowledge Base ID | `6OFPQYR1JK` | `ABC123XYZ` |
| `BEDROCK_MODEL_ID` | Bedrock model identifier | `anthropic.claude-3-haiku-20240307-v1:0` | `anthropic.claude-3-sonnet-20240229-v1:0` |

### AWS Credentials

The scanner uses standard AWS credential resolution:

1. **Environment Variables**:
   ```bash
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   ```

2. **AWS Profile** (Local development):
   ```bash
   aws configure --profile security-scanner
   export AWS_PROFILE=security-scanner
   ```

3. **IAM Roles** (EC2/ECS/Lambda):
   - Automatically detected when running on AWS services

4. **OIDC** (GitHub Actions):
   ```yaml
   - name: Configure AWS credentials
     uses: aws-actions/configure-aws-credentials@v4
     with:
       role-to-assume: arn:aws:iam::123456789012:role/GitHubActions
       aws-region: us-east-1
   ```

## Local Development Setup

### 1. Basic Configuration
```bash
# Clone repository
git clone <repository-url>
cd ai-security-scanner

# Install dependencies
pip install boto3

# Set environment variables
export AWS_REGION=us-east-1
export BEDROCK_KB_ID=your-kb-id
export BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# Configure AWS credentials
aws configure
```

### 2. Advanced Configuration
```bash
# Create .env file (not committed to git)
cat > .env << EOF
AWS_REGION=us-east-1
BEDROCK_KB_ID=6OFPQYR1JK
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
AWS_PROFILE=security-scanner
EOF

# Load environment variables
source .env

# Run scanner
python src/compliance_scanner.py
```

### 3. Multiple Environment Setup
```bash
# Development environment
export BEDROCK_KB_ID=dev-kb-123
export BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# Staging environment  
export BEDROCK_KB_ID=staging-kb-456
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Production environment
export BEDROCK_KB_ID=prod-kb-789
export BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
```

## CI/CD Configuration

### GitHub Actions

#### Repository Secrets
```yaml
# Required secrets (Settings > Secrets and variables > Actions)
AWS_ACCESS_KEY_ID: AKIA...
AWS_SECRET_ACCESS_KEY: wJalrXUt...
```

#### Repository Variables
```yaml
# Optional variables (Settings > Secrets and variables > Actions)
AWS_REGION: us-east-1
BEDROCK_KB_ID: 6OFPQYR1JK
BEDROCK_MODEL_ID: anthropic.claude-3-haiku-20240307-v1:0
```

#### Workflow Configuration
```yaml
name: Security Scan
on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Configure AWS
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ vars.AWS_REGION || 'us-east-1' }}
    
    - name: Run Security Scan
      env:
        AWS_REGION: ${{ vars.AWS_REGION || 'us-east-1' }}
        BEDROCK_KB_ID: ${{ vars.BEDROCK_KB_ID || '6OFPQYR1JK' }}
        BEDROCK_MODEL_ID: ${{ vars.BEDROCK_MODEL_ID || 'anthropic.claude-3-haiku-20240307-v1:0' }}
      run: python src/compliance_scanner.py
```

### Jenkins

#### Pipeline Configuration
```groovy
pipeline {
    agent any
    
    environment {
        AWS_REGION = credentials('aws-region')
        BEDROCK_KB_ID = credentials('bedrock-kb-id')
        BEDROCK_MODEL_ID = credentials('bedrock-model-id')
    }
    
    stages {
        stage('Security Scan') {
            steps {
                withAWS(credentials: 'aws-credentials', region: env.AWS_REGION) {
                    sh 'python src/compliance_scanner.py'
                }
            }
        }
    }
}
```

### GitLab CI

#### .gitlab-ci.yml
```yaml
security_scan:
  stage: test
  image: python:3.11
  variables:
    AWS_REGION: $AWS_REGION
    BEDROCK_KB_ID: $BEDROCK_KB_ID
    BEDROCK_MODEL_ID: $BEDROCK_MODEL_ID
  before_script:
    - pip install boto3
  script:
    - python src/compliance_scanner.py
  artifacts:
    reports:
      junit: compliance_report.json
```

## Model Configuration

### Available Models

#### Cost-Optimized (Recommended)
```bash
# Claude 3 Haiku - Fastest, cheapest
export BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
# Cost: ~$0.008 per scan
# Speed: Fast
# Accuracy: Good
```

#### Balanced Performance
```bash
# Claude 3 Sonnet - Balanced cost/performance
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
# Cost: ~$0.024 per scan
# Speed: Medium
# Accuracy: Better
```

#### Maximum Accuracy
```bash
# Claude 3 Opus - Highest accuracy
export BEDROCK_MODEL_ID=anthropic.claude-3-opus-20240229-v1:0
# Cost: ~$0.150 per scan
# Speed: Slower
# Accuracy: Best
```

#### Latest Models
```bash
# Claude 3.5 Sonnet - Latest generation
export BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
# Cost: ~$0.030 per scan
# Speed: Fast
# Accuracy: Excellent
```

### Model Selection Guide

| Use Case | Recommended Model | Reasoning |
|----------|-------------------|-----------|
| **Development/Testing** | Claude 3 Haiku | Cost-effective, fast feedback |
| **CI/CD Pipeline** | Claude 3 Haiku | Balance cost with accuracy |
| **Production Scanning** | Claude 3.5 Sonnet | Best accuracy for critical code |
| **Large Codebases** | Claude 3 Haiku | Minimize costs at scale |
| **High-Security Projects** | Claude 3 Opus | Maximum detection accuracy |

## Knowledge Base Configuration

### S3 Bucket Setup
```bash
# Create S3 bucket for Knowledge Base documents
aws s3 mb s3://your-security-kb-docs --region us-east-1

# Upload compliance documents
aws s3 cp docs/compliance/ s3://your-security-kb-docs/ --recursive

# Set bucket policy for Bedrock access
aws s3api put-bucket-policy --bucket your-security-kb-docs --policy file://kb-bucket-policy.json
```

### Knowledge Base Creation
```bash
# Create Knowledge Base
aws bedrock-agent create-knowledge-base \
  --name "Security Compliance KB" \
  --role-arn "arn:aws:iam::123456789012:role/BedrockKBRole" \
  --knowledge-base-configuration '{
    "type": "VECTOR",
    "vectorKnowledgeBaseConfiguration": {
      "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }' \
  --storage-configuration '{
    "type": "OPENSEARCH_SERVERLESS",
    "opensearchServerlessConfiguration": {
      "collectionArn": "arn:aws:aoss:us-east-1:123456789012:collection/kb-collection",
      "vectorIndexName": "security-rules-index",
      "fieldMapping": {
        "vectorField": "vector",
        "textField": "text",
        "metadataField": "metadata"
      }
    }
  }'
```

### Data Source Configuration
```bash
# Create data source
aws bedrock-agent create-data-source \
  --knowledge-base-id "KB123456" \
  --name "Security Documents" \
  --data-source-configuration '{
    "type": "S3",
    "s3Configuration": {
      "bucketArn": "arn:aws:s3:::your-security-kb-docs",
      "inclusionPrefixes": ["compliance/", "security/"]
    }
  }'

# Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id "KB123456" \
  --data-source-id "DS123456"
```

## Regional Configuration

### Multi-Region Setup
```bash
# Primary region (US East)
export AWS_REGION=us-east-1
export BEDROCK_KB_ID=us-east-1-kb-123

# Secondary region (US West)  
export AWS_REGION=us-west-2
export BEDROCK_KB_ID=us-west-2-kb-456

# Europe region
export AWS_REGION=eu-west-1
export BEDROCK_KB_ID=eu-west-1-kb-789
```

### Region-Specific Considerations

| Region | Bedrock Availability | Knowledge Base | Latency | Cost |
|--------|---------------------|----------------|---------|------|
| `us-east-1` | ✅ All models | ✅ Available | Lowest (US) | Standard |
| `us-west-2` | ✅ All models | ✅ Available | Low (US) | Standard |
| `eu-west-1` | ✅ Most models | ✅ Available | Medium (EU) | +10% |
| `ap-southeast-1` | ✅ Limited models | ✅ Available | High (APAC) | +15% |

## Performance Tuning

### Batch Processing
```bash
# Process multiple files efficiently
export BATCH_SIZE=10
export PARALLEL_WORKERS=4
python src/compliance_scanner.py --batch-size $BATCH_SIZE --workers $PARALLEL_WORKERS
```

### Caching Configuration
```bash
# Enable Knowledge Base response caching
export ENABLE_KB_CACHE=true
export CACHE_TTL=3600  # 1 hour

# Cache directory
export CACHE_DIR=/tmp/scanner-cache
```

### Memory Optimization
```bash
# Limit memory usage for large files
export MAX_FILE_SIZE=1048576  # 1MB
export CHUNK_SIZE=10000       # 10K characters per chunk
```

## Troubleshooting Configuration

### Debug Mode
```bash
# Enable verbose logging
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run with debug output
python src/compliance_scanner.py --debug
```

### Validation Commands
```bash
# Test AWS connectivity
aws bedrock list-foundation-models --region $AWS_REGION

# Test Knowledge Base access
aws bedrock-agent get-knowledge-base --knowledge-base-id $BEDROCK_KB_ID

# Test model access
aws bedrock invoke-model \
  --model-id $BEDROCK_MODEL_ID \
  --body '{"messages":[{"role":"user","content":"test"}],"max_tokens":10}' \
  --cli-binary-format raw-in-base64-out
```

### Common Issues

#### Issue: "Model not found"
```bash
# Check available models
aws bedrock list-foundation-models --region $AWS_REGION

# Verify model ID format
echo $BEDROCK_MODEL_ID
```

#### Issue: "Knowledge Base access denied"
```bash
# Check IAM permissions
aws iam get-role --role-name BedrockKBRole

# Verify Knowledge Base status
aws bedrock-agent get-knowledge-base --knowledge-base-id $BEDROCK_KB_ID
```

#### Issue: "Region not supported"
```bash
# Check Bedrock availability
aws bedrock describe-model-invocation-job --region $AWS_REGION

# Use supported region
export AWS_REGION=us-east-1
```

## Security Configuration

### IAM Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:GetFoundationModel",
        "bedrock:ListFoundationModels"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
      ]
    },
    {
      "Effect": "Allow", 
      "Action": [
        "bedrock:Retrieve",
        "bedrock:RetrieveAndGenerate"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:knowledge-base/*"
      ]
    }
  ]
}
```

### Network Security
```bash
# VPC endpoint for Bedrock (optional)
export BEDROCK_ENDPOINT_URL=https://vpce-123456-bedrock.us-east-1.vpce.amazonaws.com

# Custom CA bundle (if needed)
export AWS_CA_BUNDLE=/path/to/ca-bundle.pem
```

This configuration guide ensures your AI Security Scanner is properly set up for any environment while maintaining security best practices and zero hardcoded values.
