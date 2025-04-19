# IAM role for CodeBuild service
resource "aws_iam_role" "default" {
  name = "${var.codebuild_name}-codebuild-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

  lifecycle {
    create_before_destroy = true
  }
}

# IAM policy permissions attached to the CodeBuild role
resource "aws_iam_role_policy" "default" {
  role = aws_iam_role.default.name

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Resource": [
      "arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:log-group:codebuild/${var.codebuild_name}/logs:*"
      ],
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "ecr:*",
        "sns:*",
        "ssm:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:*"
      ],
      "Resource": [
        "arn:aws:s3:::${var.s3_bucket}",
        "arn:aws:s3:::${var.s3_bucket_output}",
        "arn:aws:s3:::${var.s3_bucket_cache}",
        "arn:aws:s3:::${var.s3_bucket}/*",
        "arn:aws:s3:::${var.s3_bucket_output}/*",
        "arn:aws:s3:::${var.s3_bucket_cache}/*"
      ]
    }
  ]
}
EOF
}

