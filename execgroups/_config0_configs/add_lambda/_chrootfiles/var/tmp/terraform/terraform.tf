terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    # OpenTofu 1.8.8 doesn't support the template provider natively
    # We use the hashicorp/template provider for backward compatibility
    template = {
      source  = "hashicorp/template"
      version = "~> 2.2"
    }
  }
}

