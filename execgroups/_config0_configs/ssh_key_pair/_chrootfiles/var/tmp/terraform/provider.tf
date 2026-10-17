terraform {
  # The awscc provider needs Terraform 1.0.7 or later. OpenTofu runs it at any
  # version.
  required_version = ">= 1.0.7"

  required_providers {
    awscc = {
      source  = "hashicorp/awscc"
      version = "1.106.0"
    }
    aws = {
      source = "hashicorp/aws"
      # The aws_key_pair data source takes include_public_key from 4.21.0. No
      # lock file pins the provider, so this stays on 6.x, as in ec2_keypair.
      version = "~> 6.0"
    }
  }
}

provider "awscc" {
  region = var.aws_default_region
}

provider "aws" {
  region = var.aws_default_region
}
