# AWS Key Pair Module

This OpenTofu module creates an AWS key pair that can be used for EC2 instances.

## Usage

```hcl
module "aws_key_pair" {
  source = "path/to/module"

  aws_default_region = "eu-west-1"
  key_name           = "my-key-pair"
  public_key         = "BASE64_ENCODED_PUBLIC_KEY"
}
```

## Requirements

| Name | Version |
|------|---------|
| opentofu | >= 1.8.8 |
| aws | >= 5.0.0 |

## Resources

| Name | Type |
|------|------|
| [aws_key_pair.default](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/key_pair) | resource |

## Inputs

| Name | Description | Type | Required |
|------|-------------|------|----------|
| aws_default_region | The AWS region to deploy resources (e.g., eu-west-1) | string | yes |
| key_name | Name for the AWS key pair to be created | string | yes |
| public_key | Base64 encoded public key material to import | string | yes |

## License

Copyright (C) 2025 Gary Leong <gary@config0.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.