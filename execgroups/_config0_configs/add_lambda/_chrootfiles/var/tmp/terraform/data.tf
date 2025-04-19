data "aws_caller_identity" "current" {}

data "template_file" "policy" {
  template = base64decode(var.policy_template_hash)
  vars = {
    aws_default_region = var.aws_default_region
    aws_account_id     = data.aws_caller_identity.current.account_id
  }
}

