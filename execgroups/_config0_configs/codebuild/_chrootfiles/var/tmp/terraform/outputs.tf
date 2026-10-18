output "arn" {
  description = "The ARN of the CodeBuild project"
  value       = module.codebuild.project_arn
}

output "project_name" {
  description = "The name of the CodeBuild project"
  value       = module.codebuild.project_name
}

output "cache_bucket_name" {
  description = "The S3 cache bucket the module made for the project"
  value       = module.codebuild.cache_bucket_name
}

output "service_role" {
  description = "The ARN of the IAM service role of the CodeBuild project"
  value       = module.codebuild.role_arn
}

output "environment" {
  description = "The build environment as given to the module: compute_type, image, type, privileged_mode"
  value = {
    compute_type    = var.compute_type
    image           = var.build_image
    type            = var.image_type
    privileged_mode = var.privileged_mode
  }
}
