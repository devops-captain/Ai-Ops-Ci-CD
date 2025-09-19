resource "aws_db_instance" "main" {
  identifier         = "main-db"
  engine             = "mysql"
  engine_version     = "8.0"
  instance_class     = "db.t3.micro"
  allocated_storage  = 20
  storage_encrypted  = true
  db_name            = "app"
  username           = "admin"
  password           = var.db_password
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

  deletion_protection  = true
}

resource "aws_security_group" "db" {
  name        = "database-sg"
  description = "Security group for database"

  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["<your-cidr>"] # Replace with your actual CIDR
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_kms_key" "db_key" {
  description = "KMS key for encrypting database"
}

resource "aws_vpc" "main" {
  cidr_block = "<your-vpc-cidr>" # Replace with your actual VPC CIDR
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}