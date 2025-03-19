# AWS SSH Key Upload

## Description
This stack uploads and configures an SSH key for use with AWS services. It retrieves an existing SSH public key from various sources and registers it with AWS.

## Variables

### Required
| Name | Description | Default |
|------|-------------|---------|
| key_name | SSH key identifier for resource access |  |
| public_key | SSH public key content |  |

### Optional
| Name | Description | Default |
|------|-------------|---------|
| name | Configuration for name |  |
| aws_default_region | Default AWS region | eu-west-1 |

## Features
- Retrieves SSH public keys from multiple sources including ssh_key_pair resources, ssh_public_key resources, or inputvars
- Automatically handles base64 encoding of public keys when needed
- Uploads the key to AWS for use with services like EC2

## Dependencies

### Substacks
- [config0-publish:::tf_executor](https://api-app.config0.com/web_api/v1.0/stacks/config0-publish/tf_executor)

### Execgroups
- [config0-publish:::aws::ssh_key_upload](https://api-app.config0.com/web_api/v1.0/exec/groups/config0-publish/aws/ssh_key_upload)

## License
Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.