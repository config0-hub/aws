**Description**
  - The stack creates IAM credentials to be queried and used by other automation.

**Required**

| argument      | description                            | var type | default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| policy_name   | policy name                 | string   | None         |
| iam_name   | iam name                 | string   | None         |

**Optional**

| argument           | description                            | var type |  default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| allows_hash   | the allows statement as a 64 hash | string   | see_below |
| denies_hash   | the denies statement as a 64 hash | string   | see_below |

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
                "lambda:*",
                "codebuild:*",
                "codepipeline:*",
                "execute-api:*",
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

```

