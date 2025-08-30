resource "aws_s3_bucket" "public_data" {
  bucket = "public-app-data"
}

resource "aws_s3_bucket_policy" "public_access" {
  bucket = aws_s3_bucket.public_data.id
  
  policy = jsonencode({
    Statement = [{
      Effect = "Allow"
      Principal = "*"
      Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
      Resource = "${aws_s3_bucket.public_data.arn}/*"
    }]
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
    Statement = [{
      Effect = "Allow"
      Action = "*"
      Resource = "*"
    }]
  })
}

resource "aws_iam_user_policy_attachment" "admin_attach" {
  user       = aws_iam_user.service_user.name
  policy_arn = aws_iam_policy.admin_policy.arn
}
