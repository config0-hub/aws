**Description**
  - The stack creates IAM instance role to be associated to an ec2 instance

**Required**

| argument      | description                            | var type | default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| role_name   | role_name                  | string   | None         |
| iam_instance_profile   | iam_instance_profile                  | string   | None         |
| iam_role_policy_name   | iam_role_policy_name                  | string   | None         |

**Optional**

| argument           | description                            | var type |  default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| aws_default_region   | aws_default_region   | string   | us-east-1         |
| assume_policy   | the overall the assume_policy in a json string serialized in base64    | string   | None         |
| policy   | the overall the policy in a json string serialized in base64    | string   | None         |

**Example YML Entry**
```
global_arguments:
   aws_default_region: eu-west-1
labels:
   general:
     environment: dev
     purpose: test
   infrastructure:
     cloud: aws
     product: iam
infrastructure:
   iam-role:
       stack_name: config0-hub:::aws_iam_role
       arguments:
          role_name: eval-config0-role
          iam_instance_profile: eval-config0-role
          iam_role_policy_name: eval-config0-role
       labels:
          - general
          - infrastructure
       credentials:
           - reference: aws
             orchestration: true
```

**Policy Defaults**
```
the default policy is below:

variable "policy" {
  default = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
            "s3:*",
            "ecr:*",
            "ec2:*",
            "ssm:*",
            "eks:*",
            "rds:*",
            "dynamodb:*",
        ],
      ],
      "Effect": "Allow",
      "Resource": "*"
    }
  ]
}
EOF
}

default="eyJWZXJzaW9uIjogIjIwMTItMTAtMTciLCAiU3RhdGVtZW50IjogW3siQWN0aW9uIjogWyJzMzoqIiwgImVjcjoqIiwgImVjMjoqIiwgInNzbToqIiwgImVrczoqIiwgInJkczoqIiwgImR5bmFtb2RiOioiXSwgIlJlc291cmNlIjogIioiLCAiRWZmZWN0IjogIkFsbG93In1dfQ=="

the default assume_policy is below:

variable "assume_policy" {
  default = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

default="ewogICJWZXJzaW9uIjogIjIwMTItMTAtMTciLAogICJTdGF0ZW1lbnQiOiBbCiAgICB7CiAgICAgICJBY3Rpb24iOiAic3RzOkFzc3VtZVJvbGUiLAogICAgICAiUHJpbmNpcGFsIjogewogICAgICAgICJTZXJ2aWNlIjogImVjMi5hbWF6b25hd3MuY29tIgogICAgICB9LAogICAgICAiRWZmZWN0IjogIkFsbG93IiwKICAgICAgIlNpZCI6ICIiCiAgICB9CiAgXQp9Cg=="

```
