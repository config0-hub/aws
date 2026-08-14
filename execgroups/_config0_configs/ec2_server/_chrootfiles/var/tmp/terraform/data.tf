# Account identity for the server record's SSM target facts.
data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# AWS AMI data source
# Retrieves the most recent AMI based on filters
data "aws_ami" "default" {
  most_recent = true
  owners      = [var.ami_owner]

  filter {
    name   = "name"
    values = [var.ami_filter]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

