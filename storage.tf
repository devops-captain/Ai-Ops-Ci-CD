resource "aws_s3_bucket" "public_data" {
  bucket = "public-app-data"
  
  server_side_encryption_configuration = {
    Rule = {
      ApplyServerSideEncryptionByDefault = {
        SSEAlgorithm = "AES256"
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
}

resource "aws_s3_bucket_policy" "public_access" {
  bucket = aws_s3_bucket.public_data.id
  
  policy = jsonencode({
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = []
        }
        Action = "s3:GetObject"
        Resource = "${aws_s3_bucket.public_data.arn}/*"
      }
    ]
  })
}

resource "aws_iam_user" "service_user" {
  name = "service-user"
}

resource "aws_iam_access_key" "service_key" {
  user = aws_iam_user.service_user.name
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