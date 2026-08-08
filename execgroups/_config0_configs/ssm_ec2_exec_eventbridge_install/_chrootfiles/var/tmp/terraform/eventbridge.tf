# ---------------------------------------------------------------------------
# Two completion paths.
#
# (a) The normal, fast path: EventBridge delivers the SSM "EC2 Command
#     Invocation Status-change Notification" for a terminal status straight to
#     the callback Lambda.
# (b) The safety net: a rate(1 minute) schedule drives the fallback Lambda,
#     which scans for still-open records and reconciles any that reached a
#     terminal SSM status but whose event was missed.
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
  description         = "Drive the fallback reconciler once a minute to close any run whose terminal SSM event was missed."
  schedule_expression = "rate(1 minute)"

  tags = local.tags
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
