output "sns_topic_arn" {
  description = "ARN of the created SNS topic"
  value       = aws_sns_topic.builds.arn
}

output "cloudwatch_name" {
  description = "Name of the CloudWatch event rule"
  value       = aws_cloudwatch_event_rule.builds.name
}

output "cloudwatch_arn" {
  description = "ARN of the CloudWatch event rule"
  value       = aws_cloudwatch_event_rule.builds.arn
}

output "sns_topic_subscription" {
  description = "The SNS topic subscription details showing source and destination"
  value       = "${aws_sns_topic_subscription.sns.topic_arn} -> ${aws_sns_topic_subscription.sns.endpoint}"
}

output "endpoint" {
  description = "The Lambda endpoint that receives the SNS notifications"
  value       = aws_sns_topic_subscription.sns.endpoint
}

