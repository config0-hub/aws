# AWS SNS Topic for CodeBuild Notifications
#
# This module creates an SNS topic that receives CodeBuild notifications
# and forwards them to a Lambda function.

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "builds" {
  statement {
    sid    = "TrustCloudWatchEvents"
    effect = "Allow"
    actions = [
      "sns:Publish",
      "sns:SetTopicAttributes",
      "sns:GetTopicAttributes",
      "sns:Subscribe"
    ]
    resources = [aws_sns_topic.builds.arn]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

