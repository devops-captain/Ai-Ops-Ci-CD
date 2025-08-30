# Vulnerable infrastructure for AI fixer testing
resource "aws_security_group" "web_app" {
  name        = "web-app-sg"
  description = "Security group for web application"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # WILL BE FIXED: SSH open to world
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # WILL BE FIXED: HTTP open to world
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_s3_bucket" "app_storage" {
  bucket = "my-app-storage-bucket"
  # WILL BE FIXED: Missing encryption
}

resource "aws_instance" "web_server" {
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "t3.micro"
  
  vpc_security_group_ids = [aws_security_group.web_app.id]
  
  tags = {
    Name = "WebServer"
  }
}
