################
# Secure S3 Bucket
################
resource "aws_s3_bucket" "secure" {
  bucket = "secure-bucket-example"

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

  public_access_block {
    block_public_acls       = true
    block_public_policy     = true
    ignore_public_acls      = true
    restrict_public_buckets = true
  }
}

################
# Secure Security Group
################
resource "aws_security_group" "secure_sg" {
  name        = "secure-sg"
  description = "Secure SG"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "SSH from trusted IPs"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    cidr_blocks     = ["10.0.0.0/8"] # Restrict SSH access to VPC CIDR
  }

  ingress {
    description     = "HTTPS from anywhere"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    cidr_blocks     = ["0.0.0.0/0"] # Allow HTTPS access from anywhere
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"] # Restrict outbound traffic to only necessary destinations
  }
}

data "aws_vpc" "default" {
  default = true
}

################
# Secure RDS Database
################
resource "aws_secretsmanager_secret" "db_password" {
  name = "db-password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 16
  special = true
}

resource "aws_db_instance" "secure_db" {
  identifier              = "secure-db"
  allocated_storage       = 20
  engine                  = "mysql"
  engine_version          = "5.7"
  instance_class          = "db.t3.micro"
  name                    = "securedb"
  username                = "admin"
  password                = data.aws_secretsmanager_secret_version.db_password.secret_string
  skip_final_snapshot     = true
  publicly_accessible     = false
  storage_encrypted       = true
  vpc_security_group_ids  = [aws_security_group.secure_sg.id]
  backup_retention_period = 7
  monitoring_interval     = 60
}