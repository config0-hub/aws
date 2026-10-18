# AWS Provider Configuration
# Configures the AWS provider with region and default tagging strategy

# Local block to sort tags for consistent ordering
locals {
  # Convert user-provided tags map to sorted list
  sorted_cloud_tags = [
    for k in sort(keys(var.cloud_tags)) : {
      key   = k
      value = var.cloud_tags[k]
    }
  ]

  # Create a sorted and consistent map of all tags
  all_tags = merge(
    # Convert sorted list back to map
    { for item in local.sorted_cloud_tags : item.key => item.value },
    {
      # Tag indicating resources are managed by config0
      orchestrated_by = "config0"
    }
  )
}

provider "aws" {
  # Region where AWS resources will be created
  region = var.aws_default_region

  # Default tags applied to all resources with consistent ordering
  default_tags {
    tags = local.all_tags
  }

  # Optional: Configure tags to be ignored by the provider
  ignore_tags {
    # Uncomment and customize if specific tags should be ignored
    # keys = ["TemporaryTag", "AutomationTag"]
  }
}

# Terraform Version Configuration
terraform {
  # cloudposse/codebuild/aws 2.0.2 needs OpenTofu or Terraform >= 1.3
  required_version = ">= 1.3"

  required_providers {
    aws = {
      source = "hashicorp/aws"
      # cloudposse/codebuild/aws 2.0.2 needs >= 5.0. No lock file pins the
      # provider, so init resolves the newest release that satisfies this.
      version = ">= 5.0"
    }
  }
}
