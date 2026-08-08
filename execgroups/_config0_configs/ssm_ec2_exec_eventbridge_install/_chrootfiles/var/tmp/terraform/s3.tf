# ---------------------------------------------------------------------------
# S3 bucket for SSM native command output (stdout/stderr) + payload staging.
# Locked down: no public access, SSE, TLS-only, 30-day expiration.
# force_destroy so a verification instance can be torn down without
# hand-emptying the bucket first.
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "logs" {
  bucket        = local.bucket_name
  force_destroy = true

  tags = local.tags
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "expire-30-days"
    status = "Enabled"

    filter {}

    expiration {
      days = var.s3_log_expiration_days
    }
  }
}

# Deny non-TLS access everywhere, and grant only the same-account PutObject
# needed for SSM native-output delivery (OutputS3BucketName/OutputS3KeyPrefix
# = native-output/, written by the SSM agent under the instance role's own
# identity). Reads (payload/manifest) are covered by the instance role's own
# scoped identity policy in iam.tf, not by this resource policy.
resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id

  depends_on = [aws_s3_bucket_public_access_block.logs]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.logs.arn,
          "${aws_s3_bucket.logs.arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "SameAccountNativeOutputWrite"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.account_id}:root"
        }
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.logs.arn}/native-output/*"
      }
    ]
  })
}
