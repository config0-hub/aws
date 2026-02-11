resource "aws_sns_topic" "builds" {
  name = var.topic_name
  tags = var.cloud_tags

  delivery_policy = jsonencode({
    http = {
      defaultHealthyRetryPolicy = {
        minDelayTarget     = 20
        maxDelayTarget     = 20
        numRetries         = 1
        numMaxDelayRetries = 0
        numNoDelayRetries  = 0
        numMinDelayRetries = 0
        backoffFunction    = "linear"
      }
      disableSubscriptionOverrides = false
      defaultThrottlePolicy = {
        maxReceivesPerSecond = 1
      }
    }
  })

  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_sns_topic_subscription" "sns" {
  topic_arn = aws_sns_topic.builds.arn
  protocol  = "lambda"
  endpoint  = "arn:aws:lambda:${var.aws_default_region}:${data.aws_caller_identity.current.account_id}:function:${var.lambda_name}"
}

resource "aws_lambda_permission" "allow_sns_invoke" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.builds.arn
}

resource "aws_sns_topic_policy" "builds_events" {
  arn    = aws_sns_topic.builds.arn
  policy = data.aws_iam_policy_document.builds.json
}

resource "aws_cloudwatch_event_rule" "builds" {
  name = "codebuild-to-${var.topic_name}"
  event_pattern = jsonencode({
    source      = ["aws.codebuild"]
    detail-type = ["CodeBuild Build State Change"]
    detail = {
      "build-status" = ["STOPPED", "FAILED", "SUCCEEDED"]
    }
  })
  tags = var.cloud_tags
}

resource "aws_cloudwatch_event_target" "builds" {
  target_id = "codebuild-to-${var.topic_name}"
  rule      = aws_cloudwatch_event_rule.builds.name
  arn       = aws_sns_topic.builds.arn
}