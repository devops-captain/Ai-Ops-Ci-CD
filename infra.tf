resource "aws_security_group" "app" {
  name = "app-sg"
  
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
}

resource "aws_s3_bucket" "storage" {
  bucket = "app-storage"
}

resource "aws_instance" "server" {
  ami           = "ami-12345"
  instance_type = "t3.micro"
  
  user_data = <<-EOF
    #!/bin/bash
    export SECRET="password123"
  EOF
}
