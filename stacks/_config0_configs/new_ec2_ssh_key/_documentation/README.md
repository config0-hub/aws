# EC2 SSH Key Management

## Description

This stack creates and uploads SSH keys to AWS EC2. It first generates a new SSH key pair and then uploads the public key to EC2, making it available for use with EC2 instances.

## Variables

### Required

None explicitly required, but either `key_name` or `name` must be set.

### Optional

| Name | Description | Default |
|------|-------------|---------|
| name | Configuration for name | &nbsp; |
| key_name | SSH key identifier for resource access | &nbsp; |
| schedule_id | config0 builtin - id of schedule associated with a stack/workflow | &nbsp; |
| run_id | config0 builtin - id of a run for the instance of a stack/workflow | &nbsp; |
| job_instance_id | config0 builtin - id of a job instance of a job in a schedule | &nbsp; |
| job_id | config0 builtin - id of job in a schedule | &nbsp; |
| aws_default_region | Default AWS region | us-east-1 |

## Dependencies

### Substacks

- [config0-publish:::new_ssh_key](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/stacks/config0-publish/new_ssh_key/default)
- [config0-publish:::ec2_ssh_upload](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/stacks/config0-publish/ec2_ssh_upload/default)

### Execgroups

- [config0-publish:::github::lambda_trigger_stepf](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/exec/groups/config0-publish/github/lambda_trigger_stepf/default)

### Shelloutconfigs

- [config0-publish:::terraform::resource_wrapper](http://config0.http.redirects.s3-website-us-east-1.amazonaws.com/assets/shelloutconfigs/config0-publish/terraform/resource_wrapper/default)

## License
<pre>
Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.
</pre>