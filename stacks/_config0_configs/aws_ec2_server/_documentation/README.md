# AWS EC2 Server with Optional EBS Volume

## Description
This stack creates an AWS EC2 instance with an optional EBS volume attachment. It supports configuration for instance type, AMI selection, storage, and network settings.

## Variables

### Required Variables

| Name | Description | Default |
|------|-------------|---------|
| hostname | Server hostname | _random |
| ssh_key_name | Name label for SSH key | |

### Optional Variables

| Name | Description | Default |
|------|-------------|---------|
| ami_filter | AMI filter criteria | ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-* |
| ami_owner | AMI owner ID | 099720109477 |
| instance_type | EC2 instance type | t3.micro |
| associate_public_ip_address | Configuration for with public IP address | true |
| disktype | Configuration for disktype | gp2 |
| disksize | Disk size in GB | 20 |
| user_data | Base64 encoded user data script | null |
| aws_default_region | Default AWS region | eu-west-1 |
| iam_instance_profile | IAM instance profile | |
| security_group_ids | Security group ID list | |
| sg_id | Security group ID | |
| ami | AMI ID | |
| subnet_ids | Subnet ID list | |
| volume_name | Storage volume name | |
| volume_size | Storage volume size (GB) | |
| volume_mountpoint | Volume mount path | |
| volume_fstype | Volume filesystem type | |
| config_network | Configuration for config network (choices: private, public) | private |

## Features
- Automatic subnet selection from a pool
- Security group configuration
- Optional EBS volume attachment and configuration
- Customizable instance type and AMI selection

## Dependencies

### Substacks
- [config0-publish:::ebs_volume](https://api-app.config0.com/web_api/v1.0/stacks/config0-publish/ebs_volume)
- [config0-publish:::tf_executor](https://api-app.config0.com/web_api/v1.0/stacks/config0-publish/tf_executor)

### Execgroups
- [config0-publish:::aws::ec2_server](https://api-app.config0.com/web_api/v1.0/exec/groups/config0-publish/aws/ec2_server)

## License
Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.