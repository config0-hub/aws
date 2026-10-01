output "role_arn" {
  description = "The grant's access role ARN"
  value       = aws_iam_role.access.arn
}
