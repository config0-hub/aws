# /aws/vendedlogs/states/ssm_ec2_exec — Step Functions execution history logs
# (required prefix for SFN log delivery: /aws/vendedlogs/states/*).
resource "aws_cloudwatch_log_group" "sfn" {
  name              = local.sfn_log_group_name
  retention_in_days = var.log_retention_days

  tags = local.tags
}

# /ssm/ssm_ec2_exec — SSM RunCommand CloudWatchOutputConfig destination.
resource "aws_cloudwatch_log_group" "ssm" {
  name              = local.ssm_log_group_name
  retention_in_days = var.log_retention_days

  tags = local.tags
}
