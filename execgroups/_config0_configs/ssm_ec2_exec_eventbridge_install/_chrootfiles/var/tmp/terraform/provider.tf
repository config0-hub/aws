terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Standalone module (test account 570017720022). No remote backend wired
  # yet — state stays local (terraform.tfstate, gitignored). Promotion into
  # the authoring repo as a stack will pick up that repo's backend
  # conventions.
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
