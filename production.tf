resource "aws_security_group" "web_tier" {
  name        = "production-web"
  description = "Web tier security group"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["<your-allowed-ip>/32"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["<your-allowed-ip>/32"]
  }
}

resource "aws_s3_bucket" "app_data" {
  bucket = "production-app-data-${random_id.bucket.hex}"

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        bucket_key_enabled = false
        sse_algorithm     = "AES256"
      }
    }
  }

  versioning {
    enabled = true
  }

  lifecycle_rule {
    id      = "log-delivery-write"
    enabled = true

    abort_incomplete_multipart_upload_days = 7

    prefix = ""

    expiration {
      days = 365
    }
  }
}

resource "aws_s3_bucket_policy" "private_read" {
  bucket = aws_s3_bucket.app_data.id
  
  policy = jsonencode({
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = ["<your-allowed-account-id>"]
      }
      Action = ["s3:GetObject"]
      Resource = [
        "${aws_s3_bucket.app_data.arn}",
        "${aws_s3_bucket.app_data.arn}/*"
      ]
    }]
  })
}

resource "aws_iam_role" "app_role" {
  name = "production-app-role"
  
  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "app_permissions" {
  name = "production-app-policy"
  
  policy = jsonencode({
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.app_data.arn}",
          "${aws_s3_bucket.app_data.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_instance" "web_server" {
  ami           = "ami-12345678"
  instance_type = "t3.large"
  
  vpc_security_group_ids = [aws_security_group.web_tier.id]
  
  user_data = <<-EOF
    #!/bin/bash
    # Install and configure services
  EOF
  
  tags = {
    Name = "production-web-server"
  }
}

resource "aws_db_instance" "primary" {
  identifier = "production-db"
  
  engine         = "mysql"
  engine_version = "8.0"  # Updated version
  instance_class = "db.m5.large"
  
  allocated_storage = 20
  storage_encrypted = true  # Encryption enabled
  
  db_name  = "production"
  username = "admin"
  password = var.db_password  # Use a secure variable
  
  vpc_security_group_ids = [aws_security_group.web_tier.id]
  
  skip_final_snapshot = true
  publicly_accessible = false  # Database not accessible from internet
}

resource "random_id" "bucket" {
  byte_length = 4
}

`,
  "changes_made": [
    "Closed SSH port",
    "Limited HTTP and HTTPS to specific IP",
    "Closed database and Redis ports",
    "Enabled S3 bucket encryption and versioning",
    "Restricted S3 bucket policy to specific account",
    "Limited IAM role to EC2 service",
    "Removed full admin access from IAM policy",
    "Removed hardcoded secrets from user data",
    "Enabled RDS encryption",
    "Used secure variable for database password",
    "Restricted database access"
  ]
}
```