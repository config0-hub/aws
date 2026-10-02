# ecs_cluster and ecs_service are the ecs_access target fields; the outputs
# land on the resource row under these names.
output "ecs_cluster" {
  description = "The name of the ECS cluster"
  value       = aws_ecs_cluster.default.name
}

output "ecs_service" {
  description = "The name of the ECS service"
  value       = aws_ecs_service.default.name
}

output "arn" {
  description = "The ARN of the ECS service"
  value       = aws_ecs_service.default.id
}

output "cluster_arn" {
  description = "The ARN of the ECS cluster"
  value       = aws_ecs_cluster.default.arn
}

output "task_definition_arn" {
  description = "The ARN of the task definition, with its revision"
  value       = aws_ecs_task_definition.default.arn
}

output "task_role_arn" {
  description = "The ARN of the task role"
  value       = aws_iam_role.task.arn
}

output "execution_role_arn" {
  description = "The ARN of the task execution role"
  value       = aws_iam_role.execution.arn
}

output "log_group_name" {
  description = "The name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.default.name
}

output "launch_type" {
  description = "The launch type of the ECS service"
  value       = aws_ecs_service.default.launch_type
}

output "desired_count" {
  description = "The number of tasks the service keeps running"
  value       = aws_ecs_service.default.desired_count
}

output "enable_execute_command" {
  description = "Whether ECS Exec is on for the service"
  value       = aws_ecs_service.default.enable_execute_command
}
