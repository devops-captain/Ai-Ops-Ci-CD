resource "aws_db_instance" "main" {
  identifier = "main-db"
  
  engine         = "mysql"
  engine_version = "8.0"
  instance_class = "db.t3.micro"
  
  allocated_storage = 20
  storage_encrypted = true
  
  db_name  = "app"
  username = "admin"
  password = var.db_password
  
  publicly_accessible = false
  skip_final_snapshot = true
  
  vpc_security_group_ids = [aws_security_group.db.id]
  parameter_group_name   = "default.mysql8.0"
}

resource "aws_security_group" "db" {
  name        = "database-sg"
  description = "Security group for database"
  
  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["<your-vpc-cidr>/16"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}