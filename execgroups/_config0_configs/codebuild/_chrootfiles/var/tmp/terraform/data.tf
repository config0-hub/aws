# Get AWS account identity information
data "aws_caller_identity" "current" {}

# Decode and render the buildspec template with variable substitution
locals {
  buildspec_decoded = base64decode(var.buildspec_hash)

  # Apply variable substitutions
  buildspec_rendered = replace(
    replace(
      replace(
        local.buildspec_decoded,
        "$${s3_bucket}", var.s3_bucket
      ),
      "$${aws_default_region}", var.aws_default_region
    ),
    "$${aws_account_id}", data.aws_caller_identity.current.account_id
  )
}
