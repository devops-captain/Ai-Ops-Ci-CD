resource "aws_security_group" "app" {
  name        = "app-sg"
  description = "Security group for the application"
  vpc_id      = var.vpc_id
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "storage" {
  bucket = "app-storage"
  
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
  
  lifecycle_rule {
    enabled = true
    id      = "log-deletions"
    
    transition {
      days = 30
      storage_class = "GLACIER"
    }
  }
  
  block_public_access {
    block_public_acls       = true
    ignore_public_acls      = true
    restrict_public_buckets = true
  }
}

resource "aws_instance" "server" {
  ami           = "ami-12345"
  instance_type = "t3.micro"
  
  tags = {
    Name = "secure-server"
  }
  
  ebs_block_device {
    device_name = "/dev/sda1"
    volume_type = "gp2"
    encrypted   = true
    volume_size = 20
  }
  
  user_data = <<-EOF
    #!/bin/bash
    echo "root:$(aws sts get-caller-identity | jq -r .Account)" | chpasswd
    echo "password" | passwd --stdin $USER
  EOF
  
  security_groups = [aws_security_group.app.id]
  
  key_name = var.key_name
  
  require_password_after_stop = true
  require_mfa_after_stop      = true
}