# Test file with security issues
resource "aws_security_group" "web" {
  name = "web-sg"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # CRITICAL: SSH open to world
  }
  
  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # CRITICAL: Database open to world
  }
}

resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"
  # MEDIUM: No encryption configured
}

resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t3.micro"
  
  user_data = <<-EOF
    #!/bin/bash
    export DB_PASSWORD="password123"  # HIGH: Hardcoded secret
  EOF
  
  # MEDIUM: No tags for compliance
}
