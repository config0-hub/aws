variable "aws_default_region" {
  description = "The AWS region where resources will be created"
  type        = string
  default     = "us-east-1"
}

variable "ecs_cluster" {
  description = "The name of the ECS cluster"
  type        = string
}

variable "ecs_service" {
  description = "The name of the ECS service, its task definition family and its container"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs the service's tasks run in"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of VPC security group IDs to associate with the service's tasks"
  type        = list(string)
}

variable "image" {
  description = "The container image the task runs"
  type        = string
  default     = "public.ecr.aws/docker/library/nginx:stable"
}

variable "container_port" {
  description = "The port the container listens on"
  type        = number
  default     = 80
}

variable "cpu" {
  description = "The Fargate task CPU units"
  type        = number
  default     = 256
}

variable "memory" {
  description = "The Fargate task memory in MiB"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "The number of tasks the service keeps running"
  type        = number
  default     = 1
}

variable "log_retention_in_days" {
  description = "The CloudWatch log group retention in days"
  type        = number
  default     = 7
}

variable "cloud_tags" {
  description = "Additional tags as a map to apply to all resources"
  type        = map(string)
  default     = {}
}
