# AWS EC2 Server with Optional EBS Volume

## Description
This stack creates an AWS EC2 instance with an optional EBS volume attachment. It supports configuration for instance type, AMI selection, storage, and network settings.

## Variables

### Required Variables

| Name | Description | Default |
|------|-------------|---------|
| hostname | Server hostname | _random |
| ssh_key_name | Name label for SSH key | &nbsp; |

### Optional Variables

| Name | Description | Default |
|------|-------------|---------|
| ami_filter | AMI filter criteria | ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-* |
| ami_owner | AMI owner ID | 099720109477 |
| instance_type | EC2 instance type | t3.micro |
| associate_public_ip_address | Associate public IP address with instance | true |
| disktype | EBS volume type | gp2 |
| disksize | Root disk size in GB | 20 |
| user_data | Base64 encoded user data script | null |
| aws_default_region | Default AWS region | eu-west-1 |
| iam_instance_profile | IAM instance profile | &nbsp; |
| security_group_ids | Comma-delimited security group IDs | &nbsp; |
| sg_id | Single security group ID | &nbsp; |
| ami | Specific AMI ID | &nbsp; |
| subnet_ids | Comma-delimited subnet IDs | &nbsp; |
| volume_name | Additional EBS volume name | &nbsp; |
| volume_size | Additional EBS volume size in GB | &nbsp; |
| volume_mountpoint | Additional volume mount path | &nbsp; |
| volume_fstype | Additional volume filesystem type | &nbsp; |
| config_network | Network type for volume configuration (private/public) | private |

## Dependencies

### Substacks
- [config0-publish:::ebs_volume](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/stacks/config0-publish/ebs_volume/default)
- [config0-publish:::tf_executor](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/stacks/config0-publish/tf_executor/default)

### Execgroups
- [config0-publish:::aws::ec2_server](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/exec/groups/config0-publish/aws/ec2_server/default)

### Shelloutconfigs
- [config0-publish:::terraform::resource_wrapper](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/shelloutconfigs/config0-publish/terraform/resource_wrapper/default)

## License
<pre>
Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
</pre>