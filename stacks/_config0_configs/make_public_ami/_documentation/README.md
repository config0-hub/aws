**Description**

  - This will make an ami publically available.

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

**Sample entry (as substack):**

```
arguments = {"name":"app-snapshot-1"}
arguments["config_env"] = "public"
arguments["aws_default_region"] = "us-east-1"

human_description = 'Making the ami image'

inputargs = {"arguments":arguments}
inputargs["automation_phase"] = "infrastructure"
inputargs["human_description"] = human_description
stack.make_public_ami.insert(display=True,**inputargs)
```
