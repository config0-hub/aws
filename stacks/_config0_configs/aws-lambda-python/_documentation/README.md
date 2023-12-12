**Description**

  - Creates python lambda function to AWS.
  - This stack expects as an input the python lambda files as an execution group

  # TODO - cloning lambda files from github

**Required**

| argument      | description                            | var type | default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| vpc_name   | name of the vpc                 | string   | None         |

**Optional**

| *argument*           | *description*                            | *var type* |  *default*      |
| ------------- | -------------------------------------- | -------- | ------------ |
| gcloud_region        | google region to create the subnets          | string    | us-west1       |
| cloud_tags_hash | the tags for the resources in the cloud as base64 | string  | None         |

**Sample entry:**

```
```
