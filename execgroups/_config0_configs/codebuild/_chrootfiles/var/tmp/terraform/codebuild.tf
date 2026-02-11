# AWS CodeBuild project resource
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
      vpc_id             = var.vpc_id
      subnets            = var.subnet_ids
      security_group_ids = var.security_group_ids
    }
  }

  environment {
    compute_type    = var.compute_type
    image           = var.build_image
    type            = var.image_type
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
    buildspec = local.buildspec_rendered
    type      = "NO_SOURCE"
  }

  logs_config {
    cloudwatch_logs {
      group_name  = "codebuild/${var.codebuild_name}/logs"
      stream_name = "codebuild/${var.codebuild_name}/stream"
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

