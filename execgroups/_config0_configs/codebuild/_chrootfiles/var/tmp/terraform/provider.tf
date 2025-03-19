# AWS Provider Configuration
# Configures the AWS provider with region and default tagging strategy
provider "aws" {
  # Region where AWS resources will be created
  region = var.aws_default_region
  
  # Default tags applied to all resources
  default_tags {
    tags = merge(
      # User-provided cloud tags
      var.cloud_tags,
      {
        # Tag indicating resources are managed by config0
        orchestrated_by = "config0"
      }
    )
  }
  
  # Optional: Configure tags to be ignored by the provider
  ignore_tags {
    # Uncomment and customize if specific tags should be ignored
    # keys = ["TemporaryTag", "AutomationTag"]
  }
}

# Terraform Version Configuration
# Specifies the required Terraform and provider versions
terraform {
  # Minimum Terraform version required
  required_version = ">= 1.1.0"

  # Required providers with version constraints
  required_providers {
    aws = {
      source  = "hashicorp/aws"      # AWS provider source
      version = "~> 5.0"             # Compatible with AWS provider v5.x
    }
  }
}