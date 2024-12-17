**Description**

  - Creates nodejs lambda function to AWS.
  - This stack expects as an input the nodejs lambda files as an execution group

  # TODO - cloning lambda files from github

**Required**

| argument      | description                            | var type | default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| config0_lambda_execgroup_name   | name of lambda of exec group | string   | None         |
| lambda_name   | name lambda function                 | string   | None         |
| s3_bucket   | s3_bucket | string   | None         |

**Optional**

| *argument*           | *description*                            | *var type* |  *default*      |
| ------------- | -------------------------------------- | -------- | ------------ |
| aws_default_region   | default aws region               | string   | us-east-1         |
| cloud_tags_hash | the tags for the resources in the cloud as base64 | string  | None         |

**Sample entry:**

```
```
