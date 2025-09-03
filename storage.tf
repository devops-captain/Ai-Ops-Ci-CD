resource "aws_s3_bucket" "public_data" {
  bucket = "public-app-data"
  
  server_side_encryption_configuration = {
    Rule = {
      ApplyServerSideEncryptionByDefault = {
        SSEAlgorithm = "aws:kms"
        KMSMasterKeyID = "alias/aws/s3"  # Use AWS managed key for SSE
      }
    }
  }
  
  acl = "private"
  block_public_access_settings = {
    block_public_acls = true
    ignore_public_acls = true
    block_public_policy = true
    restrict_public_buckets = true
  }
  
  versioning {
    enabled = true
  }
  
  lifecycle_rule {
    id      = "log-deletion-requests"
    enabled = true
    
    abort_incomplete_multipart_upload_days = 7
    
    expiration {
      days = 365
    }
  }
  
  policy = jsonencode({
    Statement = [
      {
        Effect = "Deny"
        Principal = "*"
        Action = "s3:GetObject"
        Resource = "${aws_s3_bucket.public_data.arn}/*"
        Condition = {
          StringEquals = {
            "aws:Referer" = "https://your-allowed-domain.com"
          }
        }
      },
      {
        Effect = "Allow"
        Principal = { Service = "s3.amazonaws.com" }
        Action = "s3:GetBucketLocation"
        Resource = "${aws_s3_bucket.public_data.arn}"
      }
    ]
  })
}

resource "aws_iam_user" "service_user" {
  name = "service-user"
  
  tags = {
    Environment = "production"
  }
}

resource "aws_iam_access_key" "service_key" {
  user = aws_iam_user.service_user.name
  
  depends_on = [aws_iam_user.service_user]
}

resource "aws_iam_policy" "admin_policy" {
  name = "service-admin-policy"
  
  policy = jsonencode({
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.public_data.arn}",
          "${aws_s3_bucket.public_data.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "admin_attach" {
  user       = aws_iam_user.service_user.name
  policy_arn = aws_iam_policy.admin_policy.arn
}

resource "aws_iam_user_inline_policy" "deny_all_policy" {
  user = aws_iam_user.service_user.name
  name = "deny-all-policy"
  policy = jsonencode({
    Statement = [
      {
        Effect = "Deny"
        Action = "*"
        Resource = "*"
      }
    ]
  })
}

resource "aws_s3_bucket_public_access_block" "bucket_block" {
  bucket = aws_s3_bucket.public_data.bucket

  block_public_acls = true
  ignore_public_acls = true
  block_public_policy = true
  restrict_public_buckets = true
}