resource "aws_s3_bucket" "test" {
  bucket = "test-bucket"
  acl    = "public-read-write"
}

resource "aws_security_group" "test" {
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "test" {
  engine               = "mysql"
  password             = "admin123"
  publicly_accessible  = true
  storage_encrypted    = false
  backup_retention_period = 0
}
