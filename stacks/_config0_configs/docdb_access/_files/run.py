"""DocumentDB access grant: one IAM role and one DocumentDB user for one grantee.

One grant is one internal project, c0-access-<grant id>, and this stack runs
once for it, in two steps. First the docdb-access-user script group runs on
an existing host in the cluster's VPC, through the ssm_ec2_exec install
install_name selects, and creates the $external user whose name is the grant
role's ARN, authenticated by MONGODB-AWS, with read or readWrite on db_name.
Then the docdb-access execgroup creates the role config0-access-<grant id>,
trusted by config0-executor-remote for the grantee only until end_time. The
role needs no permissions policy: DocumentDB checks no IAM action, the role
ARN in createUser is what lets it in. The user comes first, so a failed
script leaves no role. The tf_executor write-back records the access_grant row
after a successful apply, so the row's existence proves the role exists.

The admin login never enters Config0. master_user_secret_arn is the target
docdb row's: the Secrets Manager secret where DocumentDB keeps the cluster's
master user name and password, and rotates them every seven days. The host
script reads the login from that secret on every run, so no order row, secret
row, input variable or log carries it; only the ARN travels.

Names and row fields follow the CON-11 contract (ops work-log
2026-09-24/con-11-access-requests/contract.md, section 2b). Removing the grant
runs docdb_access_destroy, which drops the user on the same host before the
role goes; nothing here deletes one.
"""

from datetime import datetime
import json
import re

from config0_publisher.terraform import TFConstructor

TARGET_KIND = "docdb"

GRANT_ID_RE = re.compile(r"^[0-9a-f]{32}\Z")
END_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _check_master_user_secret_arn(stack):
    """The secret DocumentDB made for a cluster's master login, in the grant's
    account and region: DocumentDB runs on the RDS management API, which names
    a cluster's secret rds!cluster-<id>, and the host's instance role reads
    only rds!db- and rds!cluster- secrets."""
    prefix = (f"arn:aws:secretsmanager:{stack.aws_default_region}:{stack.aws_account_id}"
              ":secret:rds!cluster-")
    if not stack.master_user_secret_arn.startswith(prefix):
        raise ValueError(f'master_user_secret_arn must start with "{prefix}", '
                         f'got "{stack.master_user_secret_arn}"')


def _check_grant(stack):
    if not GRANT_ID_RE.match(stack.grant_id):
        raise ValueError(f'grant_id must be 32 lowercase hex, got "{stack.grant_id}"')
    # UTC ISO 8601, second precision, Z suffix; strptime raises on anything else.
    datetime.strptime(stack.end_time, END_TIME_FORMAT)


def run(stackargs):

    stack = newStack(stackargs)

    stack.parse.add_required(key="grant_id",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="grantee_owner_id",
                             tags="tfvar",
                             types="str")

    # level -> the DocumentDB role on db_name: read or readWrite. The
    # docdb-access-user script applies it; the IAM role is the same.
    stack.parse.add_required(key="level",
                             types="str",
                             choices=["read", "read_write"])

    stack.parse.add_required(key="end_time",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="db_endpoint",
                             types="str")

    stack.parse.add_required(key="db_port",
                             types="str")

    stack.parse.add_required(key="db_name",
                             types="str")

    # hostname of the server record in the VPC the script runs on
    stack.parse.add_required(key="host",
                             types="str")

    # selects the ssm_ec2_exec_eventbridge install the host order runs through
    stack.parse.add_required(key="install_name",
                             types="str")

    # the target docdb row's: the secret that holds the cluster's admin login
    stack.parse.add_required(key="master_user_secret_arn",
                             types="str")

    stack.parse.add_required(key="aws_default_region",
                             tags="tfvar,db,resource,tf_exec_env",
                             types="str")

    stack.parse.add_required(key="aws_account_id",
                             tags="tfvar",
                             types="str")

    stack.add_execgroup("config0-hub:::aws::docdb-access",
                        "tf_execgroup")

    stack.add_hostgroups("config0-hub:::aws::docdb-access-user",
                         "db_user_group")

    stack.add_substack("config0-hub:::config0_core::tf_executor")

    stack.init_variables()
    stack.init_execgroups()
    stack.init_hostgroups()
    stack.init_substacks()

    _check_grant(stack)
    _check_master_user_secret_arn(stack)

    stack.set_variable("timeout", 600)

    stack.verify_variables()

    role_name = f"config0-access-{stack.grant_id}"
    role_arn = f"arn:aws:iam::{stack.aws_account_id}:role/{role_name}"

    # The script logs on with the login it reads from the secret.
    env_vars = {
        "METHOD": "create",
        "DB_ENDPOINT": stack.db_endpoint,
        "DB_PORT": stack.db_port,
        "DB_NAME": stack.db_name,
        "DB_LEVEL": stack.level,
        "DB_USER": role_arn,
        "DB_MASTER_USER_SECRET_ARN": stack.master_user_secret_arn,
    }

    stack.add_groups_to_host(display=True,
                             human_description=f"Create DocumentDB user {role_name} on {stack.db_endpoint}",
                             env_vars=json.dumps(env_vars),
                             hostname=stack.host,
                             install_name=stack.install_name,
                             groups=stack.db_user_group)

    # The host order's child runs the script; the role waits for it.
    stack.wait_all()

    tf = TFConstructor(stack=stack,
                       provider="aws",
                       execgroup_name=stack.tf_execgroup.name,
                       resource_name=role_name,
                       resource_type="access_grant")

    tf.include(values={
        "grant_id": stack.grant_id,
        "grantee_owner_id": stack.grantee_owner_id,
        "level": stack.level,
        "end_time": stack.end_time,
        "role_name": role_name,
        "role_arn": role_arn,
        "target_kind": TARGET_KIND,
        "target_name": stack.db_endpoint,
        "db_endpoint": stack.db_endpoint,
        "db_port": stack.db_port,
        "db_name": stack.db_name,
        "host": stack.host,
        "install_name": stack.install_name,
        # the $external user's name is the role ARN
        "db_user": role_arn,
        "aws_account_id": stack.aws_account_id,
        "region": stack.aws_default_region,
        "stack_fqn": stack.stackargs["stack"],
    })

    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()
