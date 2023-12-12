**Description**

  - This will verify an ami is available typically after creation.

**Required**

| *argument*           | *description*                            | *var type* |  *default*      |
| ------------- | -------------------------------------- | -------- | ------------ |
| name         | name of the ami image - should be unique                 | string   | None         |
| config_env      | the environmental where the ami information can be found     | choices: public,private   | private    |

**Optional**

| *argument*           | *description*                            | *var type* |  *default*      |
| ------------- | -------------------------------------- | -------- | ------------ |
| aws_default_region      | aws region - must be the same as where the hostname resides      | string   | us-east-1         |
| shelloutconfig      | shelloutconfig for creating ami      | string   | config0-hub:::aws::ec2_ami         |
| wait_last_run      | the time interval to check the status of the ami between retries    | int   | 60 |
| retries      | the number of retries to check the status of the ami. if you put -1, retries is infinite.    | int   | 20 |
| timeout      | the total time allocated to wait before considering the ami will never be available. | int   | 1800 |

**Sample entry (as substack):**

```
arguments = {"name":"app-snapshot-1"}
arguments["config_env"] = "public"
arguments["region"] = "us-east-1"


human_description = 'Verifying the ami image'
inputargs = { "arguments":arguments }
inputargs["automation_phase"] = "infrastructure"
inputargs["human_description"] = human_description

stack.verify_ami.insert(display=True,**inputargs)
```
