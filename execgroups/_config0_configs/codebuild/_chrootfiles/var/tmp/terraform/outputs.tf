output "service_role" {
  description = "The ARN of the IAM service role created for the CodeBuild project"
  value       = aws_codebuild_project.default.service_role
}

output "environment" {
  description = "The environment configuration of the CodeBuild project"
  value       = aws_codebuild_project.default.environment
}

output "arn" {
  description = "The ARN of the CodeBuild project"
  value       = aws_codebuild_project.default.arn
}