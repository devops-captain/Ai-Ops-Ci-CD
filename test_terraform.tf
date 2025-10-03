################
# ✅ Secure S3 Bucket
################
resource "aws_s3_bucket" "secure" {
  bucket = "secure-bucket-example"
  acl    = "private"

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

################
# ✅ Secure Security Group
################
resource "aws_security_group" "secure_sg" {
  name        = "secure-sg"
  description = "Secure SG"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Allow SSH from trusted IPs"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    cidr_blocks     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"] # Restrict to trusted IP ranges
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"] # Allow all outbound traffic
  }
}

data "aws_vpc" "default" {
  default = true
}

################
# ✅ Secure RDS Instance
################
resource "aws_db_instance" "secure_db" {
  identifier              = "secure-db"
  allocated_storage       = 20
  engine                  = "mysql"
  engine_version          = "5.7"
  instance_class          = "db.t3.micro"
  name                    = "securedb"
  username                = "admin"
  password                = random_password.db_password.result # Use a randomly generated password
  skip_final_snapshot     = true
  publicly_accessible     = false # Database is not exposed to the internet
  storage_encrypted       = true # Enable encryption at rest
  vpc_security_group_ids  = [aws_security_group.secure_sg.id]
}

resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Apply OWASP Top 10 recommendations:
# 1. Prevent Injection: Use parameterized queries for database access
# 2. Broken Authentication: Use strong, randomly generated passwords
# 3. Sensitive Data Exposure: Enable encryption at rest and in transit
# 4. XML External Entities (XXE): Not applicable in this Terraform code
# 5. Broken Access Control: Use restrictive security groups and IAM policies
# 6. Security Misconfiguration: Ensure all resources are properly configured
# 7. Cross-Site Scripting (XSS): Not applicable in this Terraform code
# 8. Insecure Deserialization: Not applicable in this Terraform code
# 9. Using Components with Known Vulnerabilities: Use latest versions of AWS resources
# 10. Insufficient Logging and Monitoring: Enable CloudTrail, CloudWatch, and other logging/monitoring services