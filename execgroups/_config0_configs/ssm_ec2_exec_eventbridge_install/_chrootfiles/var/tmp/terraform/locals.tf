locals {
  account_id = data.aws_caller_identity.current.account_id

  name_prefix = "${local.account_id}-ssm_ec2_exec_eventbridge"

  bucket_name = "ssm-ec2-exec-eventbridge-logs-${local.account_id}"

  lambda_artifacts_bucket_name = "ssm-ec2-exec-eventbridge-lambda-artifacts-${local.account_id}"

  dynamodb_table_name = "ssm_ec2_exec_eventbridge_tokens"

  starter_function_name  = "${local.name_prefix}-starter"
  callback_function_name = "${local.name_prefix}-callback"
  fallback_function_name = "${local.name_prefix}-fallback"

  sfn_log_group_name = "/aws/vendedlogs/states/ssm_ec2_exec_eventbridge"
  ssm_log_group_name = "/ssm/ssm_ec2_exec_eventbridge"

  tags = {
    ManagedBy = "config0"
    Component = "ssm-ec2-exec-eventbridge"
  }
}
