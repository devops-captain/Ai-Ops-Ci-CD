resource "aws_db_instance" "main" {
  identifier = "main-db"
  
  engine         = "mysql"
  engine_version = "5.7"
  instance_class = "db.t3.micro"
  
  allocated_storage = 20
  storage_encrypted = false
  
  db_name  = "app"
  username = "admin"
  password = "password123"
  
  publicly_accessible = true
  skip_final_snapshot = true
  
  vpc_security_group_ids = [aws_security_group.db.id]
}

resource "aws_security_group" "db" {
  name = "database-sg"
  
  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
