# EC2 SSH Key Management

## Description

This stack creates and uploads SSH keys to AWS EC2. It first generates a new SSH key pair and then uploads the public key to EC2, making it available for use with EC2 instances.

## Variables

### Required

None explicitly required, but either `key_name` or `name` must be set.

### Optional

| Name | Description | Default |
|------|-------------|---------|
| name | Configuration for name | |
| key_name | SSH key identifier for resource access | |
| schedule_id | config0 builtin - id of schedule associated with a stack/workflow | |
| run_id | config0 builtin - id of a run for the instance of a stack/workflow | |
| job_instance_id | config0 builtin - id of a job instance of a job in a schedule | |
| job_id | config0 builtin - id of job in a schedule | |
| aws_default_region | Default AWS region | us-east-1 |

## Features

- Generates a new SSH key pair
- Uploads the public key to AWS EC2
- Uses key_name or name as the identifier for the SSH key
- Supports specifying AWS region

## Dependencies

### Substacks

- [config0-publish:::new_ssh_key](https://api-app.config0.com/web_api/v1.0/stacks/config0-publish/new_ssh_key)
- [config0-publish:::ec2_ssh_upload](https://api-app.config0.com/web_api/v1.0/stacks/config0-publish/ec2_ssh_upload)

## License

Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.