################
# ❌ Anti-Patterns for S3
################
resource "aws_s3_bucket" "insecure" {
  bucket = "insecure-bucket-example"
}

# ❌ No encryption enabled
# ❌ Public ACLs allowed
# ❌ Versioning disabled

################
# ❌ Anti-Patterns for Security Groups
################
resource "aws_security_group" "insecure_sg" {
  name        = "insecure-sg"
  description = "Wide open SG"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    # ❌ Open to 0.0.0.0/0 (anyone on the internet can SSH)
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    # ❌ Allow everything without restriction
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_vpc" "default" {
  default = true
}

################
# ❌ Anti-Patterns for RDS
################
resource "aws_db_instance" "insecure_db" {
  identifier              = "insecure-db"
  allocated_storage       = 20
  engine                  = "mysql"
  instance_class          = "db.t3.micro"
  name                    = "insecuredb"
  username                = "admin"
  password                = "Password12389"     # ❌ Hardcoded weak password
  skip_final_snapshot     = true
  publicly_accessible     = true              # ❌ Database exposed to the internet
  storage_encrypted       = false             # ❌ No encryption at rest
  vpc_security_group_ids  = [aws_security_group.insecure_sg.id]
}
