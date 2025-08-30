# Production infrastructure with complex security vulnerabilities
resource "aws_security_group" "web_tier" {
  name        = "production-web"
  description = "Web tier security group"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # SSH open to world
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Database port open to world
  }

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Redis open to world
  }
}

resource "aws_s3_bucket" "app_data" {
  bucket = "production-app-data-${random_id.bucket.hex}"
  # Missing encryption, versioning, and access controls
}

resource "aws_s3_bucket_policy" "public_read" {
  bucket = aws_s3_bucket.app_data.id
  
  policy = jsonencode({
    Statement = [{
      Effect = "Allow"
      Principal = "*"  # Public access
      Action = ["s3:GetObject", "s3:ListBucket"]
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
        Service = "*"  # Overly broad principal
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
        Action = "*"  # Full admin access
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = "iam:*"  # IAM admin access
        Resource = "*"
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
    export DB_PASSWORD="SuperSecret123!"
    export API_KEY="sk-1234567890abcdef"
    export JWT_SECRET="my-super-secret-key"
    
    # Install and configure services
    mysql -u root -p"admin123" -e "CREATE DATABASE app;"
  EOF
  
  # No encryption, monitoring, or backup
}

resource "aws_db_instance" "primary" {
  identifier = "production-db"
  
  engine         = "mysql"
  engine_version = "5.7"  # Outdated version
  instance_class = "db.t3.micro"
  
  allocated_storage = 20
  storage_encrypted = false  # No encryption
  
  db_name  = "production"
  username = "admin"
  password = "password123"  # Hardcoded weak password
  
  vpc_security_group_ids = [aws_security_group.web_tier.id]
  
  skip_final_snapshot = true
  publicly_accessible = true  # Database accessible from internet
}

resource "random_id" "bucket" {
  byte_length = 4
}
