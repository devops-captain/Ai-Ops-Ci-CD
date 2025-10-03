# 📊 AI Security Scanner Dashboard

## Overview

The AI Security Scanner Dashboard provides a web-based interface to view and analyze scan results over time. Each scan report is automatically uploaded to S3 and displayed in an interactive dashboard with tabbed navigation.

## Features

- **📈 Historical Tracking**: View all scan results over time
- **🔍 Detailed Analysis**: Drill down into specific issues and compliance violations
- **📊 Visual Metrics**: Summary cards showing key statistics
- **🏷️ Tabbed Interface**: Easy navigation between different scan runs
- **🔗 S3 Integration**: Automatic report storage and retrieval
- **📱 Responsive Design**: Works on desktop and mobile devices

## Setup Instructions

### 1. Create S3 Bucket and Website

Run the automated setup script:

```bash
./setup-dashboard.sh
```

This will:
- Create an S3 bucket for reports
- Enable static website hosting
- Set appropriate bucket policies
- Upload the dashboard HTML
- Provide the dashboard URL

### 2. Manual Setup (Alternative)

If you prefer manual setup:

```bash
# Create S3 bucket
BUCKET_NAME="your-reports-bucket"
aws s3 mb s3://$BUCKET_NAME --region us-east-1

# Enable static website hosting
aws s3 website s3://$BUCKET_NAME --index-document index.html

# Set bucket policy for public read access
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://bucket-policy.json

# Update HTML with your bucket name
sed "s/YOUR_REPORTS_BUCKET_NAME/$BUCKET_NAME/g" website/index.html > website/index-configured.html

# Upload website
aws s3 cp website/index-configured.html s3://$BUCKET_NAME/index.html --content-type text/html
```

### 3. Configure Scanner

Set the environment variable to enable S3 uploads:

```bash
export REPORTS_S3_BUCKET=your-reports-bucket
```

Or add to your GitHub Actions workflow:

```yaml
env:
  REPORTS_S3_BUCKET: ${{ vars.REPORTS_S3_BUCKET }}
```

## Usage

### Running Scans with Dashboard Integration

```bash
# Local scan with S3 upload
REPORTS_S3_BUCKET=your-bucket python3 src/compliance_scanner.py

# Specific file scan
REPORTS_S3_BUCKET=your-bucket python3 src/compliance_scanner.py test_terraform.tf

# Auto-fix with dashboard
REPORTS_S3_BUCKET=your-bucket python3 src/compliance_scanner.py --fix --no-push
```

### Viewing Results

1. **Access Dashboard**: Visit your S3 website URL
2. **Browse Reports**: Click tabs to switch between different scan runs
3. **Analyze Issues**: View detailed compliance violations and remediation steps
4. **Track Progress**: Monitor improvements over time

## Dashboard Features

### Summary Metrics
- **Files Scanned**: Total number of files analyzed
- **Issues Found**: Total security violations detected
- **Scan Cost**: AI analysis cost for the scan
- **AI Calls**: Number of Bedrock API calls made

### Severity Breakdown
- **Critical**: Issues that block PR merging
- **High**: Important security vulnerabilities
- **Medium**: Moderate security concerns
- **Low**: Minor security improvements

### Compliance Tracking
- **PCI-DSS**: Payment card industry violations
- **HIPAA**: Healthcare data protection issues
- **GDPR**: Privacy regulation violations
- **SOC2**: Service organization control issues
- **OWASP**: Web application security problems

### Detailed Issue View
- **File Location**: Exact file and line number
- **Issue Description**: AI-generated explanation
- **Compliance Mapping**: Which standards are violated
- **S3 Sources**: Links to Knowledge Base documents
- **Remediation**: Suggested fixes

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Scanner Run   │───▶│  JSON Report     │───▶│  S3 Bucket      │
│   (Local/CI)    │    │  Generated       │    │  /reports/      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Browser   │◀───│  S3 Website      │◀───│  Dashboard HTML │
│   (User)        │    │  (Static Host)   │    │  (JavaScript)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## File Structure

```
website/
├── index.html              # Main dashboard HTML
└── README.md              # Website documentation

scripts/
├── setup-dashboard.sh     # Automated setup script
└── test-s3-upload.sh     # Test S3 functionality

src/
└── compliance_scanner.py # Updated with S3 upload
```

## Configuration Options

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `REPORTS_S3_BUCKET` | S3 bucket for reports | `ai-security-reports` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | AWS credentials | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials | `wJalr...` |

### GitHub Actions Variables

Add these to your repository variables:

```yaml
REPORTS_S3_BUCKET: your-reports-bucket-name
AWS_REGION: us-east-1
```

## Security Considerations

### Bucket Permissions
- Reports bucket allows public read access for dashboard
- Use IAM policies to restrict write access to scanner only
- Consider VPC endpoints for private access

### Data Privacy
- Reports may contain sensitive file paths and code snippets
- Use private buckets if handling sensitive codebases
- Implement bucket lifecycle policies for data retention

### Access Control
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::ACCOUNT:user/scanner"},
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::reports-bucket/reports/*"
    }
  ]
}
```

## Troubleshooting

### Common Issues

#### Dashboard shows "No reports found"
```bash
# Check if reports are being uploaded
aws s3 ls s3://your-bucket/reports/

# Verify bucket policy allows public read
aws s3api get-bucket-policy --bucket your-bucket
```

#### S3 upload fails
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify bucket exists and permissions
aws s3 ls s3://your-bucket/
```

#### CORS errors in browser
```bash
# Add CORS configuration to bucket
aws s3api put-bucket-cors --bucket your-bucket --cors-configuration file://cors.json
```

### Debug Mode

Enable debug logging for S3 operations:

```bash
DEBUG=true REPORTS_S3_BUCKET=your-bucket python3 src/compliance_scanner.py
```

## Advanced Features

### Custom Styling
Modify `website/index.html` to customize:
- Color scheme and branding
- Additional metrics and charts
- Custom filtering and search
- Export functionality

### Integration with Other Tools
- **Slack Notifications**: Add webhook calls after S3 upload
- **JIRA Integration**: Create tickets for critical issues
- **Metrics Collection**: Send data to CloudWatch or Datadog

### Automation
```bash
# Scheduled scans with dashboard updates
0 0 * * * REPORTS_S3_BUCKET=your-bucket /path/to/scanner.py
```

## Cost Considerations

### S3 Costs
- **Storage**: ~$0.023 per GB per month
- **Requests**: ~$0.0004 per 1,000 PUT requests
- **Data Transfer**: Free for same-region access

### Typical Monthly Costs
- **Small Team** (10 scans): ~$0.10
- **Medium Team** (100 scans): ~$1.00
- **Large Team** (1000 scans): ~$10.00

The dashboard adds minimal cost (~$0.001 per scan) for S3 storage and hosting.

## Future Enhancements

### Planned Features
- **Real-time Updates**: WebSocket integration for live updates
- **Advanced Analytics**: Trend analysis and reporting
- **Team Collaboration**: Comments and issue assignment
- **API Integration**: REST API for programmatic access

### Community Contributions
- Custom dashboard themes
- Additional chart types and visualizations
- Integration with popular development tools
- Mobile app for dashboard access

This dashboard provides a comprehensive view of your security posture over time, making it easy to track improvements and identify trends in your codebase security.
