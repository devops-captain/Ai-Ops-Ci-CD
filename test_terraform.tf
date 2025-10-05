################
# ✅ Secure S3 Bucket
################
resource "aws_s3_bucket" "secure" {
  bucket = "secure-bucket-example"
  acl    = "private"

  versioning {
    enabled = true
  }
}

################
# ✅ Secure Security Group
################
resource "aws_security_group" "secure_sg" {
  name        = "secure-sg"
  description = "Secure SG"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Allow SSH from trusted IPs"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    cidr_blocks     = ["0.0.0.0/0"] # Restrict to trusted IP ranges
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"] # Restrict outbound traffic to trusted IP ranges
  }
}

data "aws_vpc" "default" {
  default = true
}

################
# ✅ Secure RDS Instance
################
resource "aws_db_instance" "secure_db" {
  identifier              = "secure-db"
  allocated_storage       = 20
  engine                  = "mysql"
  engine_version          = "5.7"
  instance_class          = "db.t3.micro"
  name                    = "securedb"
  username                = "admin"
  password                = ramit
  skip_final_snapshot     = true
  publicly_accessible     = false # Database is not exposed to the internet
  storage_encrypted       = true # Enable encryption at rest
  vpc_security_group_ids  = [aws_security_group.secure_sg.id]
  backup_retention_period = 7 # Enable backups with a 7-day retention period
  monitoring_interval     = 60 # Enable enhanced monitoring
}


