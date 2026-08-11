# ---------------------------------------------------------------------------
# Two completion paths.
#
# (a) The normal, fast path: EventBridge delivers the SSM "EC2 Command
#     Invocation Status-change Notification" for a terminal status straight to
#     the callback Lambda.
# (b) The safety net: a rate(15 minutes) schedule drives the fallback Lambda,
#     which reconciles missed terminal events and closes overdue commands.
#
# The invocation-status event's detail carries hyphenated keys
# (command-id / instance-id / status). The terminal status set below is a
# superset of the four DESIGN calls out (Success, Failed, Cancelled,
# TimedOut) — Undeliverable/Terminated are also genuinely terminal, so
# matching them only closes runs sooner; anything not matched here still gets
# closed by the fallback.
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "ssm_invocation_terminal" {
  name        = "${local.name_prefix}-ssm-invocation-terminal"
  description = "SSM command invocation reached a terminal status -> release the SFN task token via the callback Lambda."

  event_pattern = jsonencode({
    source      = ["aws.ssm"]
    detail-type = ["EC2 Command Invocation Status-change Notification"]
    detail = {
      status = ["Success", "Failed", "Cancelled", "TimedOut", "Undeliverable", "Terminated"]
    }
  })

  tags = local.tags

  provisioner "local-exec" {
    when        = destroy
    interpreter = ["python3", "-c"]
    command     = <<-PY
      import boto3

      rule_name = ${jsonencode(self.name)}
      events = boto3.client("events")
      targets = events.list_targets_by_rule(Rule=rule_name)["Targets"]
      target_ids = [target["Id"] for target in targets]
      if target_ids:
          result = events.remove_targets(Rule=rule_name, Ids=target_ids)
          if result["FailedEntryCount"] != 0:
              raise RuntimeError(
                  f"failed to remove EventBridge targets: {result['FailedEntries']}"
              )
    PY
  }
}

resource "aws_cloudwatch_event_target" "callback" {
  rule      = aws_cloudwatch_event_rule.ssm_invocation_terminal.name
  target_id = "callback-lambda"
  arn       = aws_lambda_function.callback.arn
}

resource "aws_lambda_permission" "allow_eventbridge_callback" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.callback.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ssm_invocation_terminal.arn
}

resource "aws_cloudwatch_event_rule" "fallback_schedule" {
  name                = "${local.name_prefix}-fallback-schedule"
  description         = "Drive the global fallback reconciler every 15 minutes to close missed terminal events and overdue commands."
  schedule_expression = "rate(15 minutes)"

  tags = local.tags

  provisioner "local-exec" {
    when        = destroy
    interpreter = ["python3", "-c"]
    command     = <<-PY
      import boto3

      rule_name = ${jsonencode(self.name)}
      events = boto3.client("events")
      targets = events.list_targets_by_rule(Rule=rule_name)["Targets"]
      target_ids = [target["Id"] for target in targets]
      if target_ids:
          result = events.remove_targets(Rule=rule_name, Ids=target_ids)
          if result["FailedEntryCount"] != 0:
              raise RuntimeError(
                  f"failed to remove EventBridge targets: {result['FailedEntries']}"
              )
    PY
  }
}

resource "aws_cloudwatch_event_target" "fallback" {
  rule      = aws_cloudwatch_event_rule.fallback_schedule.name
  target_id = "fallback-lambda"
  arn       = aws_lambda_function.fallback.arn
}

resource "aws_lambda_permission" "allow_eventbridge_fallback" {
  statement_id  = "AllowExecutionFromSchedule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fallback.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.fallback_schedule.arn
}
