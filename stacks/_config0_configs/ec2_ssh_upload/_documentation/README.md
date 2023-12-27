**Description**

  - The stack uploads ssh public key to ec2.
  - The stack requires name or key_name of the public key
  - The stack will first look at public_key in the variables
  - The stack will second look at public_key in the Config0's inputvars
  - The stack will thirdly look at public_key in the Config0's resources

**Optional**

| argument           | description                            | var type |  default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| aws_default_region   | default aws region               | string   | us-east-1         |
| key_name   | name of the ssh key                 | string   | None         |
| name   | name of the ssh key                 | string   | None         |
| public_key   | public_key in base64                | string   | None         |

**Sample entry**

```
infrastructure:
   ssh_upload:
       stack_name: config0-hub:::ec2_ssh_upload
       arguments:
          name: config0-test-ec2-key
       credentials:
           - reference: ec2
             orchestration: true
```
