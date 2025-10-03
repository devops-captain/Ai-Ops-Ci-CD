# 🔒 AI-Powered Compliance Security Scanner

An intelligent security scanner that uses Amazon Bedrock AI models and Knowledge Base to detect compliance violations across multiple languages and frameworks with real-time rule traceability.

## 🚀 Key Features

- **Multi-Language Support**: Python, JavaScript, Terraform, Kubernetes, Go, Java, C#
- **AI-Powered Detection**: Uses Amazon Bedrock (Claude 3 Haiku) for intelligent security analysis
- **Knowledge Base Integration**: Real-time rule traceability to S3-stored compliance documents
- **Compliance Standards**: PCI-DSS, SOC2, HIPAA, GDPR, OWASP Top 10
- **Auto-Fix Capability**: Automatically fixes detected security issues
- **Cost Optimized**: ~$0.01 per scan (95% cost reduction from original design)
- **CI/CD Integration**: GitHub Actions workflow with PR blocking on critical issues
- **Zero Hardcoded Values**: Fully configurable via environment variables

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Source Code   │───▶│  AI Scanner      │───▶│  Bedrock AI     │
│   (Multi-lang)  │    │  (Python)        │    │  (Claude 3)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Compliance      │◀───│  Knowledge Base  │◀───│  S3 Documents   │
│ Report (JSON)   │    │  Integration     │    │  (RFC/Standards)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📊 Comparison with Traditional Tools

| Feature | AI Scanner | OPA/Gatekeeper | Terrascan | Wiz | Checkov |
|---------|------------|-----------------|-----------|-----|---------|
| **AI-Powered** | ✅ Claude 3 | ❌ Rule-based | ❌ Rule-based | ✅ Proprietary | ❌ Rule-based |
| **Multi-Language** | ✅ 7+ languages | ❌ K8s only | ❌ IaC only | ✅ Multi | ✅ Multi |
| **Real-time Learning** | ✅ Knowledge Base | ❌ Static rules | ❌ Static rules | ✅ Cloud-based | ❌ Static rules |
| **Rule Traceability** | ✅ S3 sources | ❌ No tracing | ❌ No tracing | ❌ Proprietary | ❌ No tracing |
| **Auto-Fix** | ✅ AI-generated | ❌ Manual | ❌ Manual | ✅ Limited | ✅ Limited |
| **Cost** | 💰 $0.01/scan | 💰 Free | 💰 Free | 💰💰💰 Enterprise | 💰 Free/Paid |
| **Context Awareness** | ✅ Full context | ❌ Pattern match | ❌ Pattern match | ✅ Cloud context | ❌ Pattern match |
| **Compliance Standards** | ✅ 5+ standards | ❌ Custom policies | ✅ Limited | ✅ Extensive | ✅ Extensive |

## 🔧 Quick Start

### Prerequisites
- Python 3.11+
- AWS Account with Bedrock access
- Knowledge Base with compliance documents

### Installation
```bash
git clone <repository>
cd ai-security-scanner
pip install boto3
```

### Configuration
```bash
# Set environment variables (optional - has defaults)
export AWS_REGION=us-east-1
export BEDROCK_KB_ID=your-kb-id
export BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
```

### Usage
```bash
# Scan all files
python src/compliance_scanner.py

# Scan specific file
python src/compliance_scanner.py path/to/file.py

# Auto-fix issues
python src/compliance_scanner.py --fix

# Auto-fix without git push
python src/compliance_scanner.py --fix --no-push
```

## 📋 Sample Output

```
🔒 Compliance-Focused AI Security Scanner
Model: anthropic.claude-3-haiku-20240307-v1:0
Knowledge Base ID: 6OFPQYR1JK (configured for future use)
Standards: PCI-DSS, SOC2, HIPAA, GDPR, OWASP

📁 Scanning 4 files for compliance violations

🔍 Compliance scanning test_terraform.tf (Terraform)...
   📚 KB Query successful - 2 sources found
   Found 8 issues
   📋 Compliance violations: PCI-DSS, SOC2, HIPAA, GDPR

============================================================
📊 Compliance Scan Results
============================================================
Files scanned: 4
Issues found: 25
AI calls: 4
Cost: $0.0088

🎯 Severity:
  CRITICAL: 6
  HIGH: 9
  MEDIUM: 8

📋 Compliance Violations:
  PCI-DSS: 25 issues in 4 files
    ⚠️  6 critical, 9 high
  HIPAA: 23 issues in 4 files
    ⚠️  6 critical, 9 high

🚨 Top Issues:

test_terraform.tf (Terraform):
  [CRITICAL] Line 8: S3 bucket does not have encryption enabled
    📋 Violates: PCI-DSS, HIPAA, GDPR
    🗂️ S3 Sources: s3://ai-security-kb-docs-2025/terraform_security.md
```

## 🔄 CI/CD Integration

### GitHub Actions Setup
1. Add repository secrets:
   ```
   AWS_ACCESS_KEY_ID
   AWS_SECRET_ACCESS_KEY
   ```

2. Add repository variables (optional):
   ```
   AWS_REGION=us-east-1
   BEDROCK_KB_ID=your-kb-id
   BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
   ```

3. The workflow automatically:
   - Scans on PR/push/schedule
   - Blocks PRs with critical issues
   - Generates detailed PR comments
   - Supports manual auto-fix triggers

## 📚 Knowledge Base Integration

The scanner integrates with Amazon Bedrock Knowledge Base to provide:

- **Real-time Rule Lookup**: Queries KB for relevant security rules
- **Document Traceability**: Links violations to specific S3 documents
- **Dynamic Learning**: Updates as you add new compliance documents
- **Multi-Standard Support**: PCI-DSS, SOC2, HIPAA, GDPR, OWASP

### KB Document Structure
```
s3://your-kb-bucket/
├── general_security.md      # General security rules
├── terraform_security.md    # Terraform-specific rules
├── kubernetes_security.md   # K8s security rules
└── sample_kb_content.md     # Comprehensive examples
```

## 💰 Cost Analysis

| Component | Cost per Scan | Monthly (100 scans) |
|-----------|---------------|---------------------|
| Claude 3 Haiku | $0.008 | $0.80 |
| Knowledge Base | $0.002 | $0.20 |
| **Total** | **$0.01** | **$1.00** |

**95% cost reduction** compared to original design using Claude 3 Opus.

## 🔒 Security Features

- **Zero Hardcoded Values**: All configuration via environment variables
- **AWS IAM Integration**: Uses proper AWS credentials and roles
- **Secure Knowledge Base**: Encrypted S3 storage for compliance documents
- **Audit Trail**: Complete traceability from issue to source document
- **Privacy**: Code never leaves your AWS environment

## 📖 Documentation

- [Architecture Details](docs/architecture.md)
- [Configuration Guide](docs/configuration.md)
- [Knowledge Base Setup](docs/knowledge-base.md)
- [Comparison with Other Tools](docs/comparison.md)
- [Cost Optimization](docs/cost-optimization.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- [GitHub Issues](../../issues)
- [Documentation](docs/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)

---

**Built with ❤️ using Amazon Bedrock AI**
