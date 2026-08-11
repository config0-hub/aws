# ---------------------------------------------------------------------------
# ssm_ec2_exec_eventbridge — Standard state machine, event-driven task-token
# variant.
#
# ApplyDefaults -> Merge -> ComputeCallbackTimeout ->
# InvokeStarter (lambda:invoke.waitForTaskToken) -> Choice on callback
# exit_code -> Succeeded | real Failed state. A callback timeout reads the
# execution-to-command mirror, checks SSM, and either uses the real exit code
# or cancels a command that is still running.
#
# Unlike v1, the state machine does NOT call SSM directly and the task token
# never travels to the instance. The starter Lambda receives $$.Task.Token in
# its Payload, fires SendCommand, and stores the token in DynamoDB keyed by the
# returned CommandId. The token is later released by the callback Lambda (on
# the EventBridge SSM invocation status event) or the fallback Lambda
# (scheduled reconcile), both of which report {exit_code, command_id} back to
# this task via SendTaskSuccess.
# ---------------------------------------------------------------------------

resource "aws_sfn_state_machine" "ssm_ec2_exec_eventbridge" {
  name     = local.name_prefix
  type     = "STANDARD"
  role_arn = aws_iam_role.sfn_exec.arn

  definition = templatefile("${path.module}/statemachine.asl.json", {
    starter_function_arn = aws_lambda_function.starter.arn
    token_table_name     = aws_dynamodb_table.tokens.name
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = local.tags
}
