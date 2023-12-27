**Description**

  - The stack generates ssh_key and uploads it to ec2/aws.

**Required**

| argument      | description                            | var type | default      |
| ------------- | -------------------------------------- | -------- | ------------ |
| key_name   | name of the ssh key                 | string   | None         |

**Sample entry**

```
infrastructure:
   ssh_upload:
       stack_name: config0-hub:::new_ec2_ssh_key
       arguments:
          key_name: config0-test-ec2-key
       credentials:
           - reference: aws
             orchestration: true
```
