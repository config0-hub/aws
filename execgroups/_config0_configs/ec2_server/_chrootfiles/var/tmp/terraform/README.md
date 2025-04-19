# AWS EC2 Instance Module

This module provisions an AWS EC2 instance with customizable configuration options. It handles AMI selection, instance type, storage, networking, and more through a flexible variable system.

## Features

- Dynamic AMI selection based on filters
- Configurable instance type and storage options
- Public IP association options
- Security group and subnet configuration
- IAM role attachment
- Custom user data support
- Comprehensive tagging system

## Usage

```hcl
module "ec2_instance" {
  source = "path/to/module"

  hostname     = "web-server-01"
  ssh_key_name = "my-key-pair"
  
  # Optional configurations
  instance_type    = "t3.medium"
  disksize         = 50
  security_group_ids = "sg-1234abcd,sg-5678efgh"
}
```

## Requirements

- OpenTofu 1.8.8 or compatible version
- AWS provider configured with appropriate permissions

## Input Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| hostname | Hostname for the EC2 instance, used in Name tag | string | n/a | yes |
| ssh_key_name | Name of the SSH key pair to use for the instance | string | n/a | yes |
| aws_default_region | AWS region where resources will be created | string | "us-east-2" | no |
| ami | Default AMI ID to use if not using the AMI data source | string | "ami-055750c183ca68c38" | no |
| associate_public_ip_address | Whether to associate a public IP address with the instance | bool | true | no |
| instance_type | EC2 instance type | string | "t3.micro" | no |
| disktype | EBS volume type for the root block device | string | "gp2" | no |
| disksize | Size of the root EBS volume in GB | number | 20 | no |
| user_data | Base64 encoded user data to provide when launching the instance | string | null | no |
| ami_filter | Filter pattern to locate specific AMI | string | "ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*" | no |
| ami_owner | AWS account ID of the AMI owner (Canonical for Ubuntu) | string | "099720109477" | no |
| iam_instance_profile | IAM instance profile to attach to the instance | string | null | no |
| subnet_id | VPC Subnet ID to launch the instance in | string | null | no |
| security_group_ids | Comma-separated list of security group IDs to associate with the instance | string | null | no |
| cloud_tags | Additional tags as a map to apply to all resources | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| instance_id | The ID of the created EC2 instance |
| ami | The AMI ID used for the instance |
| arn | The ARN of the created EC2 instance |
| availability_zone | The availability zone where the instance was created |
| private_dns | The private DNS name of the instance |
| private_ip | The private IP address of the instance |
| public_dns | The public DNS name of the instance |
| public_ip | The public IP address of the instance |

## Notes

- The `user_data` variable should be base64 encoded before being passed to the module
- Security groups should be passed as a comma-separated string
- Default AMI is set to Ubuntu 20.04 LTS

## License

Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.