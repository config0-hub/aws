# The CodeBuild project, its IAM service role and the role's policies, through
# the community module (CON-101, decided 2026-10-17).
data "aws_caller_identity" "current" {}

locals {
  # The aws_codebuild stack renders the buildspec and passes it base64-encoded.
  # Three placeholders are filled here because their values are only known to
  # this execgroup's run: the log bucket, the region and the account.
  buildspec = replace(
    replace(
      replace(
        base64decode(var.buildspec_hash),
        "$${s3_bucket}", var.s3_bucket
      ),
      "$${aws_default_region}", var.aws_default_region
    ),
    "$${aws_account_id}", data.aws_caller_identity.current.account_id
  )

  # VPC placement is all three inputs or none. A for expression, because a
  # conditional between this object and {} is a type error in both binaries.
  vpc_config = {
    for key, value in {
      vpc_id             = var.vpc_id
      subnets            = var.subnet_ids
      security_group_ids = var.security_group_ids
    } : key => value
    if var.vpc_id != null && var.subnet_ids != null && var.security_group_ids != null
  }

  # The service role's policy, the same statements this execgroup attached by
  # hand before the module. The module's own default statements are off
  # (default_permissions_enabled = false), so only these apply, plus the
  # module's policy for the cache bucket it makes.
  service_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:log-group:codebuild/${var.codebuild_name}/logs:*"
        ]
      },
      {
        # ssm:* also covers the deploy key: the buildspec's parameter-store
        # pulls /ec2/keypair/<key_pair_id> (ssm:GetParameters with
        # decryption). EC2 writes that parameter under the AWS-managed
        # aws/ssm key, whose policy lets account principals decrypt through
        # SSM, so no kms:Decrypt is needed.
        Effect   = "Allow"
        Action   = ["ec2:*", "ecr:*", "sns:*", "ssm:*"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = ["s3:*"]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket}",
          "arn:aws:s3:::${var.s3_bucket_output}",
          "arn:aws:s3:::${var.s3_bucket}/*",
          "arn:aws:s3:::${var.s3_bucket_output}/*"
        ]
      }
    ]
  })
}

module "codebuild" {
  source  = "cloudposse/codebuild/aws"
  version = "2.0.2"

  # The module names the project and the role after its label. Only `name` is
  # set, and label_value_case keeps codebuild_name exactly as given.
  name             = var.codebuild_name
  label_value_case = "none"

  description   = var.description
  build_timeout = var.build_timeout

  build_image        = var.build_image
  build_type         = var.image_type
  build_compute_type = var.compute_type
  privileged_mode    = var.privileged_mode

  # NO_SOURCE, and the trigger-codebuild Lambda's start_build passes no source
  # either: every build starts in an empty workspace. With the stack's inline
  # buildspec, pre_build clones the commit over SSH with the deploy key. A
  # repository that ships its own buildspec.yml gets it as buildspecOverride,
  # the empty workspace and $S3_LOCATION (the zip pkgcode-to-s3 put in S3).
  source_type   = "NO_SOURCE"
  buildspec     = local.buildspec
  artifact_type = "NO_ARTIFACTS"

  # The module makes the cache bucket (named after its label plus a random
  # suffix, force_destroy = true, lifecycle expiry after cache_expiration_days)
  # and grants the role s3:* on it. No s3_cache_bucket_name: with an existing
  # bucket the module's cache policy renders Resource = ["", "/*"], which IAM
  # rejects (Cloud Posse issue #148), so the project could never apply.
  cache_type = "S3"

  environment_variables = [
    for name, value in var.codebuild_env_vars : {
      name  = name
      value = value
      type  = "PLAINTEXT"
    }
  ]

  vpc_config = local.vpc_config

  logs_config = {
    cloudwatch_logs = {
      group_name  = "codebuild/${var.codebuild_name}/logs"
      stream_name = "codebuild/${var.codebuild_name}/stream"
    }
    s3_logs = {
      status   = "ENABLED"
      location = "${var.s3_bucket}/codebuild/logs"
    }
  }

  default_permissions_enabled = false
  custom_policy               = [local.service_policy]

  tags = merge(
    var.cloud_tags,
    {
      Product = "codebuild"
    },
  )
}
