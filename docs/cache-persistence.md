# 📋 Cache Persistence in CI/CD

## **Problem**
In CI/CD environments, the file system is ephemeral - cache files are lost between runs, causing:
- **100% API calls** on every CI/CD run
- **High AWS costs** for frequent scans
- **Slow scan times** without cache benefits

## **Solution: S3-Based Cache Persistence**

### **How It Works**
1. **Local Development**: Uses `.file_hash_cache.json` file
2. **CI/CD Environment**: Automatically uses S3 for cache persistence
3. **Smart Fallback**: Falls back to local cache if S3 unavailable
4. **Auto-Cleanup**: Removes cache entries older than 7 days

### **Architecture**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CI/CD Run 1   │───▶│  S3 Cache Bucket │◀───│   CI/CD Run 2   │
│   (Fresh scan)  │    │  (Persistent)    │    │   (Uses cache)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
    9 AI calls              Cache saved              0 AI calls
    $0.02 cost             per repository           $0.00 cost
```

## **Setup Instructions**

### **1. Create S3 Cache Bucket**
```bash
# Run setup script
./setup-s3-cache.sh your-cache-bucket-name us-east-1

# Or manually create bucket
aws s3 mb s3://ai-security-scanner-cache --region us-east-1
```

### **2. Configure GitHub Repository**
Add these repository variables:
```
S3_CACHE_BUCKET=ai-security-scanner-cache
AWS_REGION=us-east-1
AWS_ROLE_ARN=arn:aws:iam::123456789012:role/GitHubActionsRole
```

### **3. Update Workflow**
Use the provided workflow: `.github/workflows/security-scan-with-cache.yml`

## **Cache Structure**
```json
{
  "src/compliance_scanner.py": {
    "hash": "a1b2c3d4e5f6...",
    "result": {
      "filepath": "src/compliance_scanner.py",
      "issues": [...],
      "compliance_violations": [...]
    },
    "timestamp": "2024-10-10T15:30:00"
  }
}
```

## **Performance Benefits**

### **Without S3 Cache (Traditional CI/CD)**
```
Run 1: 9 AI calls, $0.02 cost
Run 2: 9 AI calls, $0.02 cost  ❌ No cache benefit
Run 3: 9 AI calls, $0.02 cost
Total: 27 AI calls, $0.06 cost
```

### **With S3 Cache Persistence**
```
Run 1: 9 AI calls, $0.02 cost (cache miss)
Run 2: 0 AI calls, $0.00 cost  ✅ Cache hit
Run 3: 1 AI call,  $0.002 cost ✅ Only changed files
Total: 10 AI calls, $0.022 cost (63% savings)
```

## **Cost Analysis**

### **S3 Storage Costs**
- **Cache file size**: ~50KB per repository
- **S3 storage cost**: $0.023/GB/month
- **Monthly cost**: ~$0.001 per repository

### **API Call Savings**
- **Without cache**: 100 runs × $0.02 = $2.00/month
- **With cache**: 100 runs × $0.004 = $0.40/month
- **Net savings**: $1.60/month per repository

### **ROI Calculation**
- **S3 cost**: $0.001/month
- **Savings**: $1.60/month
- **ROI**: 1,600% return on investment

## **Environment Detection**
The scanner automatically detects CI/CD environments:
```python
# Detects GitHub Actions
if os.getenv('GITHUB_ACTIONS') == 'true':
    use_s3_cache()

# Detects other CI systems
if os.getenv('CI') == 'true':
    use_s3_cache()
```

## **Cache Invalidation**
- **File changes**: SHA256 hash comparison
- **Time-based**: Auto-cleanup after 7 days
- **Manual**: Delete S3 objects to force refresh

## **Security**
- **IAM permissions**: Least privilege access
- **Bucket policy**: Restricts access to cache prefix
- **Encryption**: S3 server-side encryption enabled
- **Lifecycle**: Automatic cleanup of old versions

## **Troubleshooting**

### **Cache Not Loading**
```bash
# Check S3 bucket exists
aws s3 ls s3://your-cache-bucket/

# Check IAM permissions
aws sts get-caller-identity

# Check environment variables
echo $S3_CACHE_BUCKET
echo $GITHUB_ACTIONS
```

### **High Costs Despite Cache**
- Check cache hit rate in logs
- Verify file hashes are stable
- Review S3 bucket lifecycle policy

### **Cache Corruption**
```bash
# Clear cache manually
aws s3 rm s3://your-cache-bucket/cache/ --recursive

# Or delete specific repository cache
aws s3 rm s3://your-cache-bucket/cache/owner/repo/ --recursive
```

## **Best Practices**
1. **One bucket per organization** - Share cache across repositories
2. **Regular cleanup** - Use lifecycle policies
3. **Monitor costs** - Set up CloudWatch alarms
4. **Test locally** - Use `CI=true` environment variable
5. **Backup important scans** - Archive critical scan results

## **Integration Examples**

### **GitHub Actions**
```yaml
- name: Run Scanner with Cache
  env:
    S3_CACHE_BUCKET: ${{ vars.S3_CACHE_BUCKET }}
  run: python3 src/compliance_scanner.py
```

### **GitLab CI**
```yaml
security_scan:
  variables:
    S3_CACHE_BUCKET: "ai-security-scanner-cache"
    CI: "true"
  script:
    - python3 src/compliance_scanner.py
```

### **Jenkins**
```groovy
environment {
    S3_CACHE_BUCKET = 'ai-security-scanner-cache'
    CI = 'true'
}
steps {
    sh 'python3 src/compliance_scanner.py'
}
```

---

**With S3 cache persistence, the AI Security Scanner achieves enterprise-grade performance in CI/CD environments with 60%+ cost savings!**
