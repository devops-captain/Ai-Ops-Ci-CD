################
# Secure S3 Bucket
################
resource "aws_s3_bucket" "secure" {
  bucket = "my-secure-bucket"
}

################
# Secure Security Group
################
resource "aws_security_group" "secure" {
  name        = "secure-sg"
  description = "Secure SG"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "SSH from VPC"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    cidr_blocks     = ["10.0.0.0/8"]
  }

  ingress {
    description     = "HTTPS from anywhere"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    cidr_blocks     = ["0.0.0.0/0"]
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"]
  }
}

data "aws_vpc" "default" {
  default = true
}

resource "aws_db_instance" "secure_db" {
  identifier              = "secure-db"
  allocated_storage       = 20
  engine                  = "mysql"
  engine_version          = "5.7"
  instance_class          = "db.t3.micro"
  name                    = "securedb"
  username                = "admin"
  password                = lopopoop
  skip_final_snapshot     = true
  publicly_accessible     = false
  storage_encrypted       = true
  vpc_security_group_ids  = [aws_security_group.secure_sg.id]
  backup_retention_period = 7
  monitoring_interval     = 60

  manage_master_user_password = true
}

