# Web application infrastructure with security issues
resource "aws_security_group" "web" {
  name = "webapp-sg"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # SSH open to world
  }
  
  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Database open to world
  }
}

resource "aws_s3_bucket" "uploads" {
  bucket = "webapp-uploads"
  # Missing encryption
}

resource "aws_iam_role" "app_role" {
  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Principal = { Service = "*" }  # Overly broad
      Effect = "Allow"
    }]
  })
}

resource "aws_instance" "web" {
  ami           = "ami-12345"
  instance_type = "t3.micro"
  
  user_data = <<-EOF
    #!/bin/bash
    export DB_PASS="admin123"  # Hardcoded password
  EOF
}
