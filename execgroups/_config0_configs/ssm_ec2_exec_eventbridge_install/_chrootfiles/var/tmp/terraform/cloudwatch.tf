# /aws/vendedlogs/states/ssm_ec2_exec_eventbridge — Step Functions execution
# history logs (required prefix for SFN log delivery: /aws/vendedlogs/states/*).
resource "aws_cloudwatch_log_group" "sfn" {
  name              = local.sfn_log_group_name
  retention_in_days = var.log_retention_days

  tags = local.tags
}

# /ssm/ssm_ec2_exec_eventbridge — SSM RunCommand CloudWatchOutputConfig destination.
resource "aws_cloudwatch_log_group" "ssm" {
  name              = local.ssm_log_group_name
  retention_in_days = var.log_retention_days

  tags = local.tags
}

# One log group per Lambda, pre-created so retention is managed here and the
# Lambda role only needs stream-level delivery (not CreateLogGroup).
resource "aws_cloudwatch_log_group" "starter" {
  name              = "/aws/lambda/${local.starter_function_name}"
  retention_in_days = var.log_retention_days

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "callback" {
  name              = "/aws/lambda/${local.callback_function_name}"
  retention_in_days = var.log_retention_days

  tags = local.tags
}

resource "aws_cloudwatch_log_group" "fallback" {
  name              = "/aws/lambda/${local.fallback_function_name}"
  retention_in_days = var.log_retention_days

  tags = local.tags
}
