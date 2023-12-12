data "aws_caller_identity" "current" {}

data "template_file" "buildspec" {
  template = file("${path.module}/buildspec.yml.tpl")
  vars = {
      git_url=var.git_url
      s3_bucket=var.s3_bucket
      ssm_ssh_key=var.ssm_ssh_key
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
        "*"
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
  description   = "Codebuild src code to s3"
  build_timeout = "444"
  service_role  = aws_iam_role.default.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  cache {
    type     = "S3"
    location = var.s3_bucket_cache
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = var.build_image
    type         = var.image_type
    privileged_mode = var.privileged_mode

    dynamic "environment_variable" {
        for_each = var.env_vars
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
      group_name  = "log-group"
      stream_name = "log-stream"
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

#################################################################

#  source {
#    type            = "NO_SOURCE"
#  }

#data "template_file" "buildspec" {
#  template = "${file("${path.module}/buildspec.yml")}"
#}

#data "local_file" "buildspec_local" {
#    filename = "buildspec.yml"
#}

