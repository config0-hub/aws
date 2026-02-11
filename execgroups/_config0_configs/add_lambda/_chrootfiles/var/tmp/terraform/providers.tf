provider "aws" {
  region = var.aws_default_region

  default_tags {
    tags = local.all_tags
  }
}

