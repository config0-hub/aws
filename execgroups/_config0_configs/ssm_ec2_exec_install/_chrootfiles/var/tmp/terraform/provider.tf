terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Backend is injected by the platform's terraform resource_wrapper
  # (S3-backed, target account/region) — no backend block is authored here,
  # matching every other execgroup under src/authoring/aws/execgroups/.
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
