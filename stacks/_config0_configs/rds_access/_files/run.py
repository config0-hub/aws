"""RDS access grant: one IAM role and one database user for one grantee.

One grant is one internal project, c0-access-<grant id>, and this stack runs
once for it, in two steps. First the rds-access-user script group runs on an
existing host in the database's VPC, through the ssm_ec2_exec install
install_name selects, and creates the database user c0_<first 16 hex of the
grant id> with IAM authentication and the level's grants on db_name. Then the
rds-access execgroup creates the role config0-access-<grant id>, trusted by
config0-executor-remote for the grantee only until end_time, with one inline
policy for rds-db:connect as that user. The user comes first, so a failed
script leaves no role. The tf_executor write-back records the access_grant row
after a successful apply, so the row's existence proves the role exists.

The admin credentials arrive as input-variable selectors, never literals:
db_admin_user and db_admin_password each name a key of the grant project's
resolved input variables. The stack seals both values as this schedule's
secret rows and the host order reads them by secret:::<name>, so no order row
or log carries them.

Names and row fields follow the CON-11 contract (ops work-log
2026-09-24/con-11-access-requests/contract.md, section 2b). Removing the grant
runs rds_access_destroy, which drops the user on the same host before the
role goes; nothing here deletes one.
"""

from datetime import datetime
import json
import re

from config0_publisher.terraform import TFConstructor

TARGET_KIND = "rds"

GRANT_ID_RE = re.compile(r"^[0-9a-f]{32}\Z")
END_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# The admin credential arguments and the secret each is sealed as.
ADMIN_CREDENTIALS = {
    "db_admin_user": "DB_ADMIN_USER",
    "db_admin_password": "DB_ADMIN_PASSWORD",
}


def _check_grant(stack):
    if not GRANT_ID_RE.match(stack.grant_id):
        raise ValueError(f'grant_id must be 32 lowercase hex, got "{stack.grant_id}"')
    # UTC ISO 8601, second precision, Z suffix; strptime raises on anything else.
    datetime.strptime(stack.end_time, END_TIME_FORMAT)
    # MySQL and MariaDB read % in a GRANT's database name as "any characters":
    # a grant on it would reach every database on the instance.
    if "%" in stack.db_name:
        raise ValueError(f'db_name must not contain "%", got "{stack.db_name}"')


def _admin_credential(stack, key):
    """The value the argument ``key`` selects from the grant project's
    resolved input variables. The error never echoes the argument: a literal
    credential passed by mistake stays out of the log."""
    value = stack.inputvars.get(stack.get_attr(key))
    if not value:
        raise ValueError(f"{key} names no key of the grant project's input variables")
    return value


def run(stackargs):

    stack = newStack(stackargs)

    stack.parse.add_required(key="grant_id",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="grantee_owner_id",
                             tags="tfvar",
                             types="str")

    # IAM gates the log on at every level; the level picks the database
    # grants the rds-access-user script applies.
    stack.parse.add_required(key="level",
                             tags="tfvar",
                             types="str",
                             choices=["connect", "read_only", "read_write"])

    stack.parse.add_required(key="end_time",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="db_engine",
                             types="str",
                             choices=["postgres", "mysql", "mariadb"])

    stack.parse.add_required(key="db_endpoint",
                             types="str")

    stack.parse.add_required(key="db_port",
                             types="str")

    stack.parse.add_required(key="db_name",
                             types="str")

    # the DbiResourceId, or an Aurora cluster's DbClusterResourceId
    stack.parse.add_required(key="db_resource_id",
                             tags="tfvar",
                             types="str")

    # hostname of the server record in the VPC the script runs on
    stack.parse.add_required(key="host",
                             types="str")

    # selects the ssm_ec2_exec_eventbridge install the host order runs through
    stack.parse.add_required(key="install_name",
                             types="str")

    stack.parse.add_required(key="db_admin_user",
                             types="str")

    stack.parse.add_required(key="db_admin_password",
                             types="str")

    stack.parse.add_required(key="aws_default_region",
                             tags="tfvar,db,resource,tf_exec_env",
                             types="str")

    stack.parse.add_required(key="aws_account_id",
                             tags="tfvar",
                             types="str")

    stack.add_execgroup("config0-hub:::aws::rds-access",
                        "tf_execgroup")

    stack.add_hostgroups("config0-hub:::aws::rds-access-user",
                         "db_user_group")

    stack.add_substack("config0-hub:::config0_core::tf_executor")

    stack.init_variables()
    stack.init_execgroups()
    stack.init_hostgroups()
    stack.init_substacks()

    _check_grant(stack)

    stack.set_variable("timeout", 600)

    stack.verify_variables()

    role_name = f"config0-access-{stack.grant_id}"
    # 19 characters, inside MySQL's 32; the rds-access execgroup's
    # access_policy module derives the same name.
    db_user = f"c0_{stack.grant_id[:16]}"

    # Record-only secret rows; the host order reads them back. No SSM copy.
    for key in ADMIN_CREDENTIALS:
        stack.add_secret(name=key,
                         value=_admin_credential(stack, key),
                         insert_ssm=False)

    env_vars = {
        "METHOD": "create",
        "DB_ENGINE": stack.db_engine,
        "DB_ENDPOINT": stack.db_endpoint,
        "DB_PORT": stack.db_port,
        "DB_NAME": stack.db_name,
        "DB_LEVEL": stack.level,
        "DB_USER": db_user,
    }
    for key, env_name in ADMIN_CREDENTIALS.items():
        env_vars[env_name] = f"secret:::{key}"

    stack.add_groups_to_host(display=True,
                             human_description=f"Create database user {db_user} on {stack.db_endpoint}",
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
        "role_arn": f"arn:aws:iam::{stack.aws_account_id}:role/{role_name}",
        "target_kind": TARGET_KIND,
        "target_name": stack.db_endpoint,
        "db_engine": stack.db_engine,
        "db_endpoint": stack.db_endpoint,
        "db_port": stack.db_port,
        "db_name": stack.db_name,
        "db_resource_id": stack.db_resource_id,
        "host": stack.host,
        "install_name": stack.install_name,
        "db_user": db_user,
        "aws_account_id": stack.aws_account_id,
        "region": stack.aws_default_region,
        "stack_fqn": stack.stackargs["stack"],
    })

    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()
