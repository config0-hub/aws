data "aws_caller_identity" "current" {}

data "template_file" "buildspec" {
  template = base64decode(var.buildspec_hash)
  vars = {
      s3_bucket=var.s3_bucket
      aws_default_region=var.aws_default_region
      aws_account_id=data.aws_caller_identity.current.account_id
  }
}

# iam role
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

# iam policy permissions 
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


# the codebuild
resource "aws_codebuild_project" "default" {
  name          = var.codebuild_name
  description   = var.description
  build_timeout = var.build_timeout
  service_role  = aws_iam_role.default.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  cache {
    type     = "S3"
    location = var.s3_bucket_cache
  }

  dynamic "vpc_config" {
    for_each = var.vpc_id != null && var.subnet_ids != null && var.security_group_ids != null ? [1] : []
    content {
      vpc_id     = var.vpc_id
      subnets    = var.subnet_ids
      security_group_ids  = var.security_group_ids
    }
  }

  environment {
    compute_type = var.compute_type
    image        = var.build_image
    type         = var.image_type
    privileged_mode = var.privileged_mode

    dynamic "environment_variable" {
        for_each = var.codebuild_env_vars
        content {
          name  = environment_variable.key
          value = environment_variable.value
        }
    }
  }

  source {
    buildspec           = data.template_file.buildspec.rendered
    type                = "NO_SOURCE"
  }

  logs_config {
    cloudwatch_logs {
      group_name   = "codebuild/${var.codebuild_name}/logs"
      stream_name  = "codebuild/${var.codebuild_name}/stream"
    }

    s3_logs {
      status   = "ENABLED"
      location = "${var.s3_bucket}/codebuild/logs"
    }
  }

  tags = merge(
    var.cloud_tags,
    {
      Product = "codebuild"
    },
  )

}

output "service_role" {
  value = aws_codebuild_project.default.service_role
}

output "environment" {
  value = aws_codebuild_project.default.environment
}

output "arn" {
  value = aws_codebuild_project.default.arn
}
