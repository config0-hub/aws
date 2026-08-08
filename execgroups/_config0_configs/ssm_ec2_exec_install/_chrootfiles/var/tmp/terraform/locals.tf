locals {
  account_id = data.aws_caller_identity.current.account_id

  name_prefix = "${local.account_id}-ssm_ec2_exec"

  bucket_name = "ssm-ec2-exec-logs-${local.account_id}"

  sfn_log_group_name = "/aws/vendedlogs/states/ssm_ec2_exec"
  ssm_log_group_name = "/ssm/ssm_ec2_exec"

  tags = {
    ManagedBy = "terraform"
    Component = "ssm-ec2-exec"
  }
}
