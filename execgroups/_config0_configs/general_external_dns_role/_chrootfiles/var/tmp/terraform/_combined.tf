####FILE####:::provider.tf
provider "aws" {
  region = var.aws_default_region

  default_tags {
    tags = local.all_tags
  }

  ignore_tags {
    # Uncomment if specific tags should be ignored
    # keys = ["TemporaryTag", "AutomationTag"]
  }
}

terraform {
  required_version = ">= 1.1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

####FILE####:::variables.tf
variable "aws_default_region" {
  description = "AWS region for the resources"
  type        = string
  default     = "us-east-1"
}

variable "zone_ids" {
  description = "List of Route53 hosted zone IDs that ExternalDNS will manage"
  type        = list(string)
  default     = ["Z1234567890ABCDE", "Z0987654321FGHIJ"]
}

variable "role_name" {
  description = "Name of the general ExternalDNS IAM role"
  type        = string
  default     = "GeneralExternalDNS-Role"
}

variable "cloud_tags" {
  description = "User-defined map of cloud tags for AWS resources"
  type        = map(string)
  default     = {
    Environment = "production"
    Team        = "devops"
  }
}

variable "trusted_role_arns" {
  description = "List of IAM role ARNs that can assume this general role (cluster-specific bridge roles)"
  type        = list(string)
  default     = []
}

####FILE####:::locals.tf
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
    { for item in local.sorted_cloud_tags : item.key => item.value },
    {
      orchestrated_by = "config0"
    }
  )

  # List all hostedzone ARNs and the change ARN
  externaldns_zone_resources = concat(
    [for zone_id in var.zone_ids : "arn:aws:route53:::hostedzone/${zone_id}"],
    ["arn:aws:route53:::change/*"]
  )
}

####FILE####:::iam.tf
# IAM Policy for ExternalDNS Route53 permissions
resource "aws_iam_policy" "external_dns_policy" {
  name        = "${var.role_name}-Policy"
  description = "IAM policy for ExternalDNS to fully manage Route53 hosted zones"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Allow full management of DNS records in specified zones
      {
        Effect = "Allow"
        Action = [
          "route53:ChangeResourceRecordSets",
          "route53:ListResourceRecordSets",
          "route53:GetHostedZone",
          "route53:GetChange"
        ]
        Resource = local.externaldns_zone_resources
      },
      # Allow listing and discovery of hosted zones globally
      {
        Effect = "Allow"
        Action = [
          "route53:ListHostedZones",
          "route53:ListHostedZonesByName"
        ]
        Resource = "*"
      },
      # Allow discovery by tag (needed for ExternalDNS zone discovery by tag)
      {
        Effect = "Allow"
        Action = [
          "route53:ListTagsForResource"
        ]
        Resource = "arn:aws:route53:::hostedzone/*"
      }
    ]
  })

  tags = local.all_tags
}

# General ExternalDNS IAM Role (can be assumed by cluster-specific roles)
resource "aws_iam_role" "external_dns_general" {
  name        = var.role_name
  description = "General IAM role for ExternalDNS with Route53 permissions - can be assumed by cluster-specific roles"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = length(var.trusted_role_arns) > 0 ? var.trusted_role_arns : ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = "external-dns"
          }
        }
      }
    ]
  })

  tags = merge(local.all_tags, {
    Purpose = "general-external-dns"
  })
}

# Attach the policy to the general role
resource "aws_iam_role_policy_attachment" "external_dns_attach_policy" {
  role       = aws_iam_role.external_dns_general.name
  policy_arn = aws_iam_policy.external_dns_policy.arn
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

####FILE####:::outputs.tf
output "policy_arn" {
  description = "The ARN of the created IAM policy"
  value       = aws_iam_policy.external_dns_policy.arn
}

output "general_external_dns_role_arn" {
  description = "ARN of the general ExternalDNS IAM role"
  value       = aws_iam_role.external_dns_general.arn
}

output "general_external_dns_role_name" {
  description = "Name of the general ExternalDNS IAM role"
  value       = aws_iam_role.external_dns_general.name
}

output "zone_ids" {
  description = "List of Route53 hosted zone IDs being managed"
  value       = var.zone_ids
}