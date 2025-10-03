# 🔧 Troubleshooting Guide

## Common Issues and Solutions

### 1. AWS Authentication Issues

#### Issue: "Unable to locate credentials"
```bash
Error: Unable to locate credentials. You can configure credentials by running "aws configure".
```

**Solutions:**
```bash
# Option 1: Configure AWS CLI
aws configure
# Enter: Access Key ID, Secret Access Key, Region, Output format

# Option 2: Use environment variables
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1

# Option 3: Use AWS profile
export AWS_PROFILE=your-profile-name

# Option 4: Verify current credentials
aws sts get-caller-identity
```

#### Issue: "Access Denied" for Bedrock
```bash
Error: An error occurred (AccessDeniedException) when calling the InvokeModel operation
```

**Solutions:**
```bash
# Check Bedrock model access
aws bedrock list-foundation-models --region us-east-1

# Verify IAM permissions
aws iam get-user-policy --user-name your-username --policy-name BedrockAccess

# Request model access in AWS Console
# Go to: Bedrock > Model access > Request access
```

### 2. Knowledge Base Issues

#### Issue: "Knowledge Base not found"
```bash
Error: An error occurred (ResourceNotFoundException) when calling the RetrieveAndGenerate operation
```

**Solutions:**
```bash
# Verify Knowledge Base exists
aws bedrock-agent get-knowledge-base --knowledge-base-id $BEDROCK_KB_ID

# Check Knowledge Base status
aws bedrock-agent list-knowledge-bases

# Verify environment variable
echo $BEDROCK_KB_ID

# Update environment variable
export BEDROCK_KB_ID=your-correct-kb-id
```

#### Issue: "Knowledge Base query returns no results"
```bash
Warning: KB Query successful - 0 sources found
```

**Solutions:**
```bash
# Check if documents are ingested
aws bedrock-agent list-ingestion-jobs --knowledge-base-id $BEDROCK_KB_ID --data-source-id $DATA_SOURCE_ID

# Start ingestion job
aws bedrock-agent start-ingestion-job --knowledge-base-id $BEDROCK_KB_ID --data-source-id $DATA_SOURCE_ID

# Verify S3 documents exist
aws s3 ls s3://your-kb-bucket/ --recursive

# Test direct retrieval
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id $BEDROCK_KB_ID \
  --retrieval-query '{"text": "security rules"}'
```

### 3. Model Issues

#### Issue: "Model not found or access denied"
```bash
Error: An error occurred (ValidationException) when calling the InvokeModel operation: The model ID is invalid
```

**Solutions:**
```bash
# List available models
aws bedrock list-foundation-models --region $AWS_REGION

# Check model ID format
echo $BEDROCK_MODEL_ID
# Should be: anthropic.claude-3-haiku-20240307-v1:0

# Verify model access
aws bedrock get-foundation-model --model-identifier $BEDROCK_MODEL_ID

# Test model invocation
aws bedrock-runtime invoke-model \
  --model-id $BEDROCK_MODEL_ID \
  --body '{"messages":[{"role":"user","content":"test"}],"max_tokens":10}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json
```

#### Issue: "Model quota exceeded"
```bash
Error: An error occurred (ThrottlingException) when calling the InvokeModel operation
```

**Solutions:**
```bash
# Check current quotas
aws service-quotas get-service-quota \
  --service-code bedrock \
  --quota-code L-12345678

# Request quota increase
aws service-quotas request-service-quota-increase \
  --service-code bedrock \
  --quota-code L-12345678 \
  --desired-value 1000

# Implement retry logic with exponential backoff
# Add delays between requests
```

### 4. File Processing Issues

#### Issue: "No files found to scan"
```bash
📁 Scanning 0 files for compliance violations
```

**Solutions:**
```bash
# Check current directory
pwd
ls -la

# Verify file extensions
find . -name "*.py" -o -name "*.js" -o -name "*.tf" -o -name "*.yaml"

# Run from correct directory
cd /path/to/your/project
python src/compliance_scanner.py

# Specify files explicitly
python src/compliance_scanner.py file1.py file2.js
```

#### Issue: "File too large" errors
```bash
Error: File exceeds maximum size limit
```

**Solutions:**
```python
# Increase file size limit
export MAX_FILE_SIZE=2097152  # 2MB

# Or modify scanner configuration
def process_large_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Split into chunks
    chunks = split_into_chunks(content, max_size=10000)
    
    results = []
    for chunk in chunks:
        result = analyze_chunk(chunk)
        results.append(result)
    
    return merge_results(results)
```

### 5. Performance Issues

#### Issue: "Scan taking too long"
```bash
# Scan has been running for 30+ minutes
```

**Solutions:**
```bash
# Enable debug mode to see progress
export DEBUG=true
python src/compliance_scanner.py

# Reduce file count
python src/compliance_scanner.py specific_file.py

# Check for network issues
ping bedrock.us-east-1.amazonaws.com

# Monitor AWS service health
aws health describe-events --filter services=bedrock
```

#### Issue: "High memory usage"
```bash
Error: MemoryError - unable to allocate memory
```

**Solutions:**
```python
# Process files one at a time
def process_files_sequentially(files):
    for file in files:
        result = process_single_file(file)
        yield result
        # Memory cleanup
        gc.collect()

# Limit concurrent processing
import concurrent.futures
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    futures = [executor.submit(process_file, f) for f in files]
```

### 6. CI/CD Issues

#### Issue: "GitHub Actions workflow fails"
```yaml
Error: Process completed with exit code 1
```

**Solutions:**
```yaml
# Add debug steps to workflow
- name: Debug Environment
  run: |
    echo "AWS Region: $AWS_REGION"
    echo "KB ID: $BEDROCK_KB_ID"
    echo "Model ID: $BEDROCK_MODEL_ID"
    aws sts get-caller-identity

# Check secrets and variables
- name: Verify Configuration
  run: |
    if [ -z "$AWS_ACCESS_KEY_ID" ]; then
      echo "AWS_ACCESS_KEY_ID not set"
      exit 1
    fi
    
    if [ -z "$BEDROCK_KB_ID" ]; then
      echo "BEDROCK_KB_ID not set"
      exit 1
    fi

# Add error handling
- name: Run Security Scan
  run: |
    set -e  # Exit on error
    python src/compliance_scanner.py || {
      echo "Scan failed, checking logs..."
      cat error_log.txt
      exit 1
    }
```

#### Issue: "Permission denied in CI/CD"
```bash
Error: User: arn:aws:iam::123456789012:user/github-actions is not authorized
```

**Solutions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:GetFoundationModel"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agent:Retrieve",
        "bedrock-agent:RetrieveAndGenerate"
      ],
      "Resource": "*"
    }
  ]
}
```

### 7. Output and Reporting Issues

#### Issue: "Compliance report not generated"
```bash
Scan completed but no compliance_report.json found
```

**Solutions:**
```bash
# Check write permissions
ls -la compliance_report.json
chmod 644 compliance_report.json

# Verify output directory
pwd
ls -la

# Check for errors in log
cat error_log.txt

# Run with debug mode
DEBUG=true python src/compliance_scanner.py
```

#### Issue: "Invalid JSON in report"
```bash
Error: JSONDecodeError - Expecting property name enclosed in double quotes
```

**Solutions:**
```python
# Add JSON validation
import json

def save_report(report_data, filename):
    try:
        # Validate JSON before saving
        json_str = json.dumps(report_data, indent=2)
        
        with open(filename, 'w') as f:
            f.write(json_str)
            
        # Verify saved file
        with open(filename, 'r') as f:
            json.load(f)
            
    except json.JSONEncodeError as e:
        print(f"JSON encoding error: {e}")
        # Save as text for debugging
        with open(f"{filename}.debug", 'w') as f:
            f.write(str(report_data))
```

## Diagnostic Commands

### System Health Check
```bash
#!/bin/bash
# health_check.sh

echo "=== AI Security Scanner Health Check ==="

# Check Python version
echo "Python version:"
python3 --version

# Check dependencies
echo "Checking dependencies:"
pip list | grep boto3

# Check AWS credentials
echo "AWS credentials:"
aws sts get-caller-identity 2>/dev/null || echo "AWS credentials not configured"

# Check environment variables
echo "Environment variables:"
echo "AWS_REGION: $AWS_REGION"
echo "BEDROCK_KB_ID: $BEDROCK_KB_ID"
echo "BEDROCK_MODEL_ID: $BEDROCK_MODEL_ID"

# Test Bedrock access
echo "Testing Bedrock access:"
aws bedrock list-foundation-models --region ${AWS_REGION:-us-east-1} --max-items 1 2>/dev/null && echo "✅ Bedrock accessible" || echo "❌ Bedrock access failed"

# Test Knowledge Base access
if [ -n "$BEDROCK_KB_ID" ]; then
    echo "Testing Knowledge Base access:"
    aws bedrock-agent get-knowledge-base --knowledge-base-id $BEDROCK_KB_ID 2>/dev/null && echo "✅ Knowledge Base accessible" || echo "❌ Knowledge Base access failed"
fi

# Check file permissions
echo "Checking file permissions:"
ls -la src/compliance_scanner.py 2>/dev/null && echo "✅ Scanner file accessible" || echo "❌ Scanner file not found"

echo "=== Health Check Complete ==="
```

### Performance Diagnostics
```bash
#!/bin/bash
# performance_check.sh

echo "=== Performance Diagnostics ==="

# Measure scan time
echo "Running performance test..."
start_time=$(date +%s)

# Run scanner on small test file
echo "print('hello world')" > test_file.py
python src/compliance_scanner.py test_file.py > /dev/null 2>&1

end_time=$(date +%s)
duration=$((end_time - start_time))

echo "Scan duration: ${duration} seconds"

# Clean up
rm -f test_file.py compliance_report.json

# Check network latency
echo "Network latency to Bedrock:"
ping -c 3 bedrock.${AWS_REGION:-us-east-1}.amazonaws.com

echo "=== Performance Check Complete ==="
```

### Debug Mode Activation
```bash
# Enable comprehensive debugging
export DEBUG=true
export LOG_LEVEL=DEBUG
export PYTHONPATH=$PYTHONPATH:./src

# Run with verbose output
python -v src/compliance_scanner.py --debug 2>&1 | tee debug_output.log

# Analyze debug output
grep -i error debug_output.log
grep -i warning debug_output.log
```

## Error Code Reference

| Error Code | Description | Solution |
|------------|-------------|----------|
| **AWS-001** | Credentials not found | Configure AWS credentials |
| **AWS-002** | Access denied | Check IAM permissions |
| **AWS-003** | Region not supported | Use supported region |
| **KB-001** | Knowledge Base not found | Verify KB ID |
| **KB-002** | No documents found | Check ingestion status |
| **KB-003** | Query timeout | Reduce query complexity |
| **MODEL-001** | Model not found | Check model ID |
| **MODEL-002** | Model access denied | Request model access |
| **MODEL-003** | Quota exceeded | Request quota increase |
| **FILE-001** | File not found | Check file path |
| **FILE-002** | File too large | Increase size limit |
| **FILE-003** | Permission denied | Check file permissions |
| **JSON-001** | Invalid JSON output | Check data formatting |
| **NET-001** | Network timeout | Check connectivity |
| **MEM-001** | Out of memory | Reduce batch size |

## Getting Help

### Log Analysis
```bash
# Check error logs
cat error_log.txt

# Search for specific errors
grep -i "error\|exception\|failed" error_log.txt

# Check system logs (Linux/Mac)
tail -f /var/log/system.log | grep python
```

### Support Channels
1. **GitHub Issues**: Report bugs and feature requests
2. **AWS Support**: For Bedrock-specific issues
3. **Documentation**: Check docs/ folder for detailed guides
4. **Community**: Stack Overflow with tags `aws-bedrock`, `ai-security`

### Information to Include in Support Requests
1. **Environment Details**:
   - Operating system
   - Python version
   - AWS region
   - Model ID

2. **Error Information**:
   - Complete error message
   - Stack trace
   - Steps to reproduce

3. **Configuration**:
   - Environment variables (redacted)
   - File types being scanned
   - Scan parameters used

4. **Logs**:
   - error_log.txt contents
   - Debug output
   - AWS CloudTrail logs (if available)

This troubleshooting guide covers the most common issues and provides systematic approaches to diagnosis and resolution.
