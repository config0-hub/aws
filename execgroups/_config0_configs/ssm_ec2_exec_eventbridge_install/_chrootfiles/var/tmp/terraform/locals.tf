locals {
  account_id = data.aws_caller_identity.current.account_id

  # account_id is dropped from name_prefix: IAM/Lambda/EventBridge/SFN/KMS
  # names are already unique per account by AWS API, so it was decorative,
  # and the "-ssm-invocation-terminal" EventBridge rule name (64-char AWS
  # limit) needs the budget for install_name instead. S3 bucket names still
  # need account_id below since those must be globally unique.
  name_prefix = "ssm_ec2_exec_eventbridge-${var.install_name}"

  bucket_name = "ssm-ec2-exec-eventbridge-logs-${local.account_id}-${var.install_name}"

  lambda_artifacts_bucket_name = "ssm-ec2-exec-eventbridge-lambda-artifacts-${local.account_id}-${var.install_name}"

  dynamodb_table_name = "ssm_ec2_exec_eventbridge_tokens-${var.install_name}"

  starter_function_name  = "${local.name_prefix}-starter"
  callback_function_name = "${local.name_prefix}-callback"
  fallback_function_name = "${local.name_prefix}-fallback"

  sfn_log_group_name = "/aws/vendedlogs/states/ssm_ec2_exec_eventbridge-${var.install_name}"
  ssm_log_group_name = "/ssm/ssm_ec2_exec_eventbridge-${var.install_name}"

  tags = {
    ManagedBy = "config0"
    Component = "ssm-ec2-exec-eventbridge"
  }
}
