**Description**
  - The stack that creates a ec2 server on aws.

**Required**

| argument      | description                            | var type | default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| hostname   | hostname of the ec2 server                 | string   | None         |
| ssh_key_name   | key_name for the ec2 server                 | string   | None         |
| aws_default_region   | default aws region               | string   | us-east-1         |
| vpc_id   | the vpc_id to be used        | string    | None |
| subnet_id   | the subnet_id to be used        | string    | None |
| security_group_ids   | the security_group_ids to be used        | csv (string)    | None |

**Optional**

| argument           | description                            | var type |  default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| config_network   | the configuration network                | choice public/private   | private |
| register_to_db   | register the ec2 instance to Config0               | boolean   | True |
| ami   | the ami ami               | string   | None |
| ami_filter   | the AMI filter used for searches      | string       | Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-\*  | 
| ami_owner   | the AMI owner used for searches        | string    | 099720109477 (canonical) |
| instance_type   | the instance type        | string    | t2.micro |
| disksize   | the instance root disk size        | integer    | 40 |
| volume_name   | the name of volume to be attached        | string    | None |
| volume_size   | the size of volume to be created        | integer    | None |
| volume_mount   | the mount point of the extra volume        | string    | None |
| volume_fstype   | the fileystem of the extra volume        | string    | None |
| iam_instance_profile   | the iam_instance_profile to attach to ec2 instance        | string    | None |
| user_data   | the user_data encoding in base64        | string    | None |
| cloud_tags_hash | the tags for the resources in the cloud as base64 | string  | None         |
