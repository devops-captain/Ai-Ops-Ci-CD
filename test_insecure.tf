# S3 Bucket Security
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

# Security Group Rules
resource "aws_security_group" "secure" {
  name = "secure-sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["YOUR_IP/32"] # Restrict to specific IP
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # HTTPS only
  }
}

# Database Security
resource "aws_db_instance" "secure" {
  identifier = "secure-db"

  publicly_accessible    = false
  storage_encrypted     = true
  deletion_protection   = true
  backup_retention_period = 7

  manage_master_user_password = true
  vpc_security_group_ids = [aws_security_group.db.id]

  # Use AWS Secrets Manager for database password
  password = data.aws_secretsmanager_secret_version.db_password.secret_string
}

data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "db-password"
}