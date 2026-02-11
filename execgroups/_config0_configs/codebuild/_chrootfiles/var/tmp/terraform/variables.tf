variable "aws_default_region" {
  description = "The AWS region where resources will be created"
  type        = string
  default     = "eu-west-1"
}

variable "build_image" {
  description = "The Docker image to use for the CodeBuild project"
  type        = string
  default     = "aws/codebuild/standard:5.0"
}

variable "image_type" {
  description = "The type of build environment to use for related builds"
  type        = string
  default     = "LINUX_CONTAINER"
}

variable "s3_bucket" {
  description = "The S3 bucket where build artifacts and logs will be stored"
  type        = string
}

variable "s3_bucket_output" {
  description = "The S3 bucket where build output artifacts will be stored"
  type        = string
}

variable "s3_bucket_cache" {
  description = "The S3 bucket where build cache will be stored"
  type        = string
}

variable "cloud_tags" {
  description = "Additional tags as a map to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "codebuild_name" {
  description = "The name of the CodeBuild project"
  type        = string
}

variable "codebuild_env_vars" {
  description = "Environmental variables for the CodeBuild project"
  type        = map(string)
  default     = {}
}

variable "privileged_mode" {
  description = "Whether to enable running the Docker daemon inside a Docker container"
  type        = bool
  default     = true
}

variable "description" {
  description = "Description of the CodeBuild project"
  type        = string
  default     = "Codebuild project"
}

variable "build_timeout" {
  description = "Number of minutes, from 5 to 480 (8 hours), for AWS CodeBuild to wait until timing out any build"
  type        = number
  default     = 5
}

variable "compute_type" {
  description = "Compute resources the build project will use"
  type        = string
  default     = "BUILD_GENERAL1_SMALL"
}

variable "buildspec_hash" {
  description = "Buildspec template as a base64 hash"
  type        = string
}

variable "vpc_id" {
  description = "The VPC ID where the CodeBuild project will run"
  type        = string
  default     = null
}

variable "subnet_ids" {
  description = "The subnet IDs where the CodeBuild project will run"
  type        = list(string)
  default     = null
}

variable "security_group_ids" {
  description = "The security group IDs to apply to the CodeBuild project"
  type        = list(string)
  default     = null
}

