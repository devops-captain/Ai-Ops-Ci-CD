resource "aws_security_group" "app" {
  name = "app-sg"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["<your-ip>/32"]
  }
  
  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["<your-ip>/32"]
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
    echo "" > /etc/passwd
  EOF
}