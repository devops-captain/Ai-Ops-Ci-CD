# Security Knowledge Base - Sample Content

## Terraform Security Rules

### S3 Bucket Security
**Problem**: Unencrypted S3 buckets
**Fix**:
```hcl
resource "aws_s3_bucket" "secure" {
  bucket = "my-secure-bucket"
  
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
  
  versioning {
    enabled = true
  }
  
  public_access_block {
    block_public_acls       = true
    block_public_policy     = true
    ignore_public_acls      = true
    restrict_public_buckets = true
  }
}
```

### Security Group Rules
**Problem**: Open security groups (0.0.0.0/0)
**Fix**:
```hcl
resource "aws_security_group" "secure" {
  name = "secure-sg"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]  # Restrict to VPC
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]   # HTTPS only
  }
}
```

### Database Security
**Problem**: Publicly accessible databases
**Fix**:
```hcl
resource "aws_db_instance" "secure" {
  identifier = "secure-db"
  
  # Security settings
  publicly_accessible    = false
  storage_encrypted     = true
  deletion_protection   = true
  backup_retention_period = 7
  
  # Use secrets manager
  manage_master_user_password = true
  
  vpc_security_group_ids = [aws_security_group.db.id]
}
```

### Secrets Management
**Problem**: Hardcoded passwords
**Fix**:
```hcl
# Use AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name = "db-password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 16
  special = true
}
```

## Kubernetes Security Rules

### Pod Security Standards
**Problem**: Privileged containers
**Fix**:
```yaml
apiVersion: v1
kind: Pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      capabilities:
        drop:
        - ALL
```

### Network Policies
**Problem**: No network segmentation
**Fix**:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-app-traffic
spec:
  podSelector:
    matchLabels:
      app: myapp
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
```

### Resource Limits
**Problem**: No resource constraints
**Fix**:
```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: app
    resources:
      limits:
        cpu: "1"
        memory: "2Gi"
      requests:
        cpu: "500m"
        memory: "1Gi"
```

## Python Security Rules

### Input Validation
**Problem**: SQL injection vulnerabilities
**Fix**:
```python
# Bad
query = f"SELECT * FROM users WHERE id = {user_id}"

# Good
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

### Secrets Management
**Problem**: Hardcoded API keys
**Fix**:
```python
import os
from boto3 import client

# Bad
api_key = "sk-1234567890abcdef"

# Good
api_key = os.environ.get('API_KEY')
# Or use AWS Secrets Manager
secrets_client = client('secretsmanager')
secret = secrets_client.get_secret_value(SecretId='api-key')
api_key = secret['SecretString']
```

## Docker Security Rules

### Base Images
**Problem**: Using latest or root images
**Fix**:
```dockerfile
# Bad
FROM ubuntu:latest
USER root

# Good
FROM ubuntu:22.04
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser
```

### Multi-stage Builds
**Problem**: Including build tools in production
**Fix**:
```dockerfile
# Build stage
FROM node:16 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Production stage
FROM node:16-alpine
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001
COPY --from=builder --chown=nextjs:nodejs /app ./
USER nextjs
```

## Shell Script Security

### Input Validation
**Problem**: Command injection
**Fix**:
```bash
# Bad
eval "ls $user_input"

# Good
if [[ "$user_input" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    ls "$user_input"
else
    echo "Invalid input"
    exit 1
fi
```

### Secure Defaults
**Problem**: Unsafe script execution
**Fix**:
```bash
#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures
IFS=$'\n\t'        # Secure Internal Field Separator

# Use full paths
/usr/bin/curl -s "https://api.example.com"
```

## AWS IAM Security

### Least Privilege
**Problem**: Overly broad permissions
**Fix**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::specific-bucket/*"
    }
  ]
}
```

### MFA Requirements
**Problem**: No MFA for sensitive operations
**Fix**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
}
```

## Compliance Mappings

### CIS Controls
- **CIS 3.3**: Secure configurations for network infrastructure
- **CIS 5.1**: Establish secure configurations for operating systems
- **CIS 16.1**: Maintain an inventory of authentication systems

### SOC 2 Type II
- **CC6.1**: Logical and physical access controls
- **CC6.7**: Data transmission and disposal
- **CC7.1**: System operations

### NIST Framework
- **PR.AC-1**: Identity management and access control
- **PR.DS-1**: Data-at-rest protection
- **PR.DS-2**: Data-in-transit protection
