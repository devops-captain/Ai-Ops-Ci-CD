# Complex infrastructure requiring AI analysis
resource "aws_iam_role" "app_role" {
  name = "application-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "*"  # COMPLEX: Overly broad principal - AI needed to detect
        }
      }
    ]
  })
}

resource "aws_iam_policy" "app_policy" {
  name = "app-permissions"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject", 
          "dynamodb:*",  # COMPLEX: Wildcard permissions - needs AI context
          "lambda:InvokeFunction",
          "secretsmanager:GetSecretValue"
        ]
        Resource = "*"  # COMPLEX: Overly broad resource access
      },
      {
        Effect = "Allow"
        Action = "iam:PassRole"  # COMPLEX: Privilege escalation risk
        Resource = "arn:aws:iam::*:role/*"
      }
    ]
  })
}

resource "aws_security_group" "database" {
  name = "database-sg"
  
  # COMPLEX: Multiple ports with conditional logic
  dynamic "ingress" {
    for_each = var.environment == "prod" ? [3306, 5432] : [3306, 5432, 6379, 27017]
    content {
      from_port   = ingress.value
      to_port     = ingress.value  
      protocol    = "tcp"
      cidr_blocks = var.environment == "prod" ? ["10.0.0.0/8"] : ["0.0.0.0/0"]
    }
  }
}

resource "aws_s3_bucket_policy" "data_bucket_policy" {
  bucket = aws_s3_bucket.data.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowPublicRead"
        Effect = "Allow"
        Principal = "*"  # COMPLEX: Public bucket access - context matters
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.data.arn}",
          "${aws_s3_bucket.data.arn}/*"
        ]
        Condition = {
          StringEquals = {
            "s3:ExistingObjectTag/public" = "true"  # COMPLEX: Conditional access
          }
        }
      }
    ]
  })
}

resource "aws_lambda_function" "processor" {
  filename         = "function.zip"
  function_name    = "data-processor"
  role            = aws_iam_role.app_role.arn
  handler         = "index.handler"
  runtime         = "python3.8"  # COMPLEX: Outdated runtime version
  
  environment {
    variables = {
      DB_CONNECTION = "postgresql://user:${var.db_password}@${aws_db_instance.main.endpoint}/mydb"
      # COMPLEX: Connection string with embedded credentials
      API_ENDPOINT = "https://api.internal.company.com"
      DEBUG_MODE   = var.environment != "prod" ? "true" : "false"
    }
  }
  
  # COMPLEX: Missing VPC configuration for sensitive function
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
  # COMPLEX: No validation, could be weak
}
