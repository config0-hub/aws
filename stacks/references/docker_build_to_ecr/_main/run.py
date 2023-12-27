class Main(newSchedStack):

    def __init__(self, stackargs):

        newSchedStack.__init__(self, stackargs)

        # Add default variables
        self.parse.add_required(key="vpc_name")
        self.parse.add_required(key="vpc_id")
        self.parse.add_required(key="subnet_ids")
        self.parse.add_required(key="sg_id")
        self.parse.add_required(key="bastion_sg_id")
        self.parse.add_required(key="docker_host")
        self.parse.add_required(
            key="src_build_groups", default="config0-hub:::gitlab::runner,config0-hub:::gitlab::runner-autoscaling")

        # docker image to execute terraform with
        self.parse.add_optional(key="aws_default_region", default="us-west-1")
        self.parse.add_optional(key="instance_type", default="t3.micro")
        self.parse.add_optional(key="disksize", default="25")
        # probably better to use inputvars
        self.parse.add_optional(key="aws_account_id")

        self.parse.add_required(key="docker_image_tag", default="latest")
        self.parse.add_required(key="docker_repo_name")

        # Add substack
        self.stack.add_substack('config0-hub:::new_ec2_ssh_key')
        self.stack.add_substack('config0-hub:::aws_iam_role')
        self.stack.add_substack('config0-hub:::ec2_ubuntu_admin')
        self.stack.add_substack('config0-hub:::docker_build_ssh')

        self.stack.init_execgroups()
        self.stack.init_substacks()

    def _get_aws_account_id(self):

        if self.stack.get_attr("aws_account_id"):
            return self.stack.aws_account_id

        aws_account_id = self.stack.inputvars.get("aws_account_id")

        if aws_account_id:
            return aws_account_id

        if not aws_account_id:
            raise Exception("aws_account_id must be provided")

    def run_build(self):

        self.stack.init_variables()

        default_values = {"aws_default_region": self.stack.aws_default_region,
                          "docker_image_tag": self.stack.docker_image_tag,
                          "docker_host": self.stack.docker_host,
                          "docker_repo_name": self.stack.docker_repo_name}  # update repo_name  # testtest110

        overide_values = {"ssh_key_name": self.stack.docker_host,
                          "aws_account_id": self._get_aws_account_id(),
                          "overide_order_timeout": 600}

        #overide_values["add_env_vars"] = add_env_vars

        for src_group in self.stack.to_list(self.stack.src_build_groups):

            inputargs = {"arguments": arguments,
                         "automation_phase": "infrastructure",
                         "display": True,
                         "default_values": default_values,
                         "overide_values": {"build_src_group": src_group}}

            self.stack.docker_build_ssh.insert(display=True, **inputargs)

        return

    def run_sshkey(self):

        self.stack.init_variables()

        ssh_key_name = self.stack.docker_host

        overide_values = {"key_name": ssh_key_name}
        default_values = {"aws_default_region": self.stack.aws_default_region}

        inputargs = {"default_values": default_values,
                     "overide_values": overide_values,
                     "automation_phase": "infrastructure",
                     "human_description": f'Create and upload ssh key name {ssh_key_name}'}

        return self.stack.new_ec2_ssh_key.insert(display=True, **inputargs)

    def run_iam_role(self):

        self.stack.init_variables()

        self.stack.set_variable("role_name", 
                                "{}-role".format(self.stack.docker_host))

        self.stack.set_variable("iam_instance_profile",
                                "{}-profile".format(self.stack.docker_host))

        self.stack.set_variable("iam_role_policy_name",
                                "{}-policy".format(self.stack.docker_host))

        overide_values = {"role_name": self.stack.role_name,
                          "iam_instance_profile": self.stack.iam_instance_profile,
                          "iam_role_policy_name": self.stack.iam_role_policy_name
                          }

        default_values = {"aws_default_region": self.stack.aws_default_region}

        inputargs = {"default_values": default_values,
                     "overide_values": overide_values,
                     "automation_phase": "infrastructure",
                     "human_description": f'Create IAM role for {self.stack.docker_host}'}

        return self.stack.aws_iam_role.insert(display=True, **inputargs)

    def run_docker_host(self):

        self.stack.init_variables()

        self.stack.set_variable("iam_instance_profile",
                                "{}-profile".format(self.stack.docker_host))

        user_data_hash = self.stack.b64_encode('echo "cloud-init done"')

        overide_values = {"hostname": self.stack.docker_host,
                          "spot": True,
                          "ip_key": "public_ip",
                          "user_data_hash": user_data_hash,
                          "ssh_key_name": self.stack.docker_host,
                          "iam_instance_profile": self.stack.iam_instance_profile,
                          "publish_to_saas": True}

        default_values = {"vpc_name": self.stack.vpc_name,
                          "vpc_id": self.stack.vpc_id,
                          "subnet_ids": self.stack.subnet_ids,
                          "size": self.stack.instance_type,
                          "disksize": self.stack.disksize,
                          "aws_default_region": self.stack.aws_default_region,
                          "sg_id": self.stack.bastion_sg_id,
                          }

        inputargs = {"default_values": default_values,
                     "overide_values": overide_values,
                     "automation_phase": "infrastructure",
                     "human_description": f'Create EC2 admin {self.stack.docker_host}'}

        return self.stack.ec2_ubuntu_admin.insert(display=True, **inputargs)

    def run(self):

        self.stack.unset_parallel()
        self.add_job("sshkey")
        self.add_job("iam_role")
        self.add_job("docker_host")
        self.add_job("build")

        return self.finalize_jobs()

    def schedule(self):

        sched = self.new_schedule()
        sched.job = "sshkey"
        sched.archive.timeout = 1200
        sched.archive.timewait = 120
        sched.conditions.retries = 1
        sched.automation_phase = "infrastructure"
        sched.human_description = "upload user public ssh key"
        sched.on_success = ["iam_role"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "iam_role"
        sched.archive.timeout = 1800
        sched.archive.timewait = 120
        sched.automation_phase = "infrastructure"
        sched.human_description = "Create IAM role"
        sched.on_success = ["docker_host"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "docker_host"
        sched.archive.timeout = 1800
        sched.archive.timewait = 120
        sched.automation_phase = "infrastructure"
        sched.human_description = "Create EC2 for docker_host"
        sched.on_success = ["build"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "build"
        sched.archive.timeout = 3600
        sched.archive.timewait = 120
        sched.automation_phase = "infrastructure"
        sched.human_description = "Build and push container"
        self.add_schedule()

        return self.get_schedules()
