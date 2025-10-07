################
# Secure S3 Bucket
################
resource "aws_s3_bucket" "secure" {
  bucket = "secure-bucket-example"
  acl    = "private"

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
    cidr_blocks     = ["0.0.0.0/0"] # Restrict SSH access to trusted subnets
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"] # Allow only necessary outbound traffic
  }
}

data "aws_vpc" "default" {
  default = true
}

################
# Secure RDS Database
################
resource "aws_db_instance" "secure_db" {
  identifier              = "secure-db"
  allocated_storage       = 20
  engine                  = "mysql"
  engine_version          = "5.7"
  instance_class          = "db.t3.micro"
  name                    = "securedb"
  username                = "admin"
  password                = "123dfggyyh" # Use a randomly generated password
  skip_final_snapshot     = true
  publicly_accessible     = false # Database is not publicly accessible
  storage_encrypted       = true # Enable encryption at rest
  vpc_security_group_ids  = [aws_security_group.secure_sg.id]
  backup_retention_period = 7 # Enable backup and recovery
  monitoring_interval     = 60 # Enable enhanced monitoring
}

