data "aws_caller_identity" "current" {}

resource "aws_cloudwatch_event_rule" "builds" {
  name          = "codebuild-${var.codebuild_name}-evntbrdg"
  event_pattern = <<EOF
{
    "source": ["aws.codebuild"],
    "detail-type": ["CodeBuild Build State Change"],
    "detail": {
      "build-status": ["STOPPED", "FAILED", "SUCCEEDED"]
    }
}
EOF
}

output "cloudwatch_name" {
  value = aws_cloudwatch_event_rule.builds.name
}

output "cloudwatch_arn" {
  value = aws_cloudwatch_event_rule.builds.arn
}
