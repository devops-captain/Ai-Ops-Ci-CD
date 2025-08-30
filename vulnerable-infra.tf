# Vulnerable Terraform configuration for testing AI security analyzer
resource "aws_security_group" "web_server" {
  name        = "web-server-sg"
  description = "Security group for web server"

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
    cidr_blocks = ["0.0.0.0/0"]  # CRITICAL: MySQL open to world
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "app_data" {
  bucket = "my-app-data-${random_id.bucket.hex}"
  # MEDIUM: No encryption configured
}

resource "aws_instance" "web" {
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "t3.micro"
  
  vpc_security_group_ids = [aws_security_group.web_server.id]
  
  user_data = <<-EOF
    #!/bin/bash
    export DB_PASSWORD="supersecret123"  # HIGH: Hardcoded password
    export API_KEY="sk-1234567890abcdef"  # HIGH: Hardcoded API key
  EOF
  
  # MEDIUM: No tags for compliance
}

resource "aws_db_instance" "main" {
  identifier = "main-db"
  
  engine         = "mysql"
  instance_class = "db.t3.micro"
  
  allocated_storage = 20
  
  db_name  = "appdb"
  username = "admin"
  password = "password123"  # CRITICAL: Hardcoded DB password
  
  skip_final_snapshot = true
  # MEDIUM: No encryption at rest
}

resource "random_id" "bucket" {
  byte_length = 4
}
