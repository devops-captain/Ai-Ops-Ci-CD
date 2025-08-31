resource "aws_db_instance" "main" {
  identifier         = "main-db"
  engine             = "mysql"
  engine_version     = "8.0"
  instance_class     = "db.t3.micro"
  allocated_storage  = 20
  storage_encrypted  = true
  db_name            = "app"
  username           = "admin"
  password           = "ashish123!"  # Password should be hashed and managed securely
  publicly_accessible = false
  skip_final_snapshot = true

  vpc_security_group_ids = [aws_security_group.db.id]
  parameter_group_name   = "default.mysql8.0"

  backup_retention_period = 7
  preferred_backup_window = "03:00-04:00"
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.db_key.arn

  multi_az                = false
  storage_type            = "io1"
  iops                    = 100

  tags = {
    Environment = "production"
    CreatedBy   = "terraform"
  }

  # Additional security settings
  skip_name_resolve = true
  backup_role       = "arn:aws:iam::123456789012:role/RDSCustomRole"
}

resource "aws_security_group" "db" {
  name        = "database-sg"
  description = "Security group for database"

  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "tcp"
    cidr_blocks = var.vpc_cidr
  }
}

resource "aws_kms_key" "db_key" {
  description = "KMS key for encrypting database"
}

variable "allowed_cidr" {
  description = "Allowed CIDR for database access"
  type        = string
  sensitive   = true
}

variable "vpc_cidr" {
  description = "VPC CIDR"
  type        = string
}