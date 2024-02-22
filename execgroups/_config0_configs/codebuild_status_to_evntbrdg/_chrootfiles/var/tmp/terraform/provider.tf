provider "aws" {
  region = var.aws_default_region
  default_tags {
    tags = merge(
      var.cloud_tags,
      {
        orchestrated_by = "config0"
      },
    )
  }
}

terraform {
  required_version = ">= 1.1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}
