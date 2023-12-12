**Description**

  - The stack connects triggers lambda when any codebuild completes.

  - This assumes the sns topic, codebuild project, and lambda function are already created.

**Required**

| argument           | description                            | var type |  default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| topic_name   | the name of the sns topic to trigger lambda function             | string   |        |
| lambda_name   | the lambda function to trigger when codebuild completes               | string   |        |

**Optional**

| argument           | description                            | var type |  default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| aws_default_region   | default aws region               | string   | us-east-1         |
| cloud_tags_hash | the tags for the resources in the cloud as base64 | string  | None         |

**Sample entry**

```
```
