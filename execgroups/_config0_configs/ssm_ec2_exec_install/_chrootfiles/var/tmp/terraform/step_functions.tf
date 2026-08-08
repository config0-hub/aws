# ---------------------------------------------------------------------------
# ssm_ec2_exec — Standard state machine, task-token variant.
#
# ApplyDefaults -> Merge -> SendCommand.waitForTaskToken (AWS-RunShellScript,
# TimeoutSeconds from input) -> Choice on callback exit_code -> Succeeded |
# real Failed state.
#
# The task token travels to the instance via the SendCommand Parameters
# bootstrap (first command line: `export TASK_TOKEN="<token>"`); the remote
# wrapper (Phase 2) sources that and calls
# `aws stepfunctions send-task-success --task-token "$TASK_TOKEN"
#  --task-output '{"exit_code": N}'` after it finishes. Phase 1 verification
# hand-rolls that callback directly in the SSM command script.
# ---------------------------------------------------------------------------

resource "aws_sfn_state_machine" "ssm_ec2_exec" {
  name     = local.name_prefix
  type     = "STANDARD"
  role_arn = aws_iam_role.sfn_exec.arn

  definition = templatefile("${path.module}/statemachine.asl.json", {
    bucket_name        = aws_s3_bucket.logs.bucket
    ssm_log_group_name = local.ssm_log_group_name
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = local.tags
}
