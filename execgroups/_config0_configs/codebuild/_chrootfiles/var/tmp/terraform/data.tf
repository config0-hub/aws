# Get AWS account identity information
data "aws_caller_identity" "current" {}

# Decode and render the buildspec template with variable substitution
data "template_file" "buildspec" {
  template = base64decode(var.buildspec_hash)
  vars = {
    s3_bucket          = var.s3_bucket
    aws_default_region = var.aws_default_region
    aws_account_id     = data.aws_caller_identity.current.account_id
  }
}

