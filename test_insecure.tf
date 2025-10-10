resource "aws_s3_bucket" "bad" {
  bucket = "my-bucket"
  acl    = "private"

  }
}

resource "aws_security_group" "bad" {
  name = "bad-sg"
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "bad" {
  engine               = "mysql"
  username             = "admin"
  password             = lolooo[kljkj
  publicly_accessible  = false
  storage_encrypted    = true
}
