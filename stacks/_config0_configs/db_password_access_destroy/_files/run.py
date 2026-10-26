"""Remove a database password access grant: the destroy INSTRUCTION of a
db_password grant project.

The grant project's destroy anchor runs this stack (saas-api
``ACCESS_DESTROY_STACKS``) with the grant's persistent arguments plus the
generic callback_delete ones: parallel_ids names the one grant schedule. A
host order has no destroy of its own, so this stack first runs the
db-password-access-user script group with METHOD=destroy on the same host,
which drops the user c0_<first 16 hex of the grant id> (a missing user is
done). On postgres and mysql, an RDS
database, the script logs on with the admin login it reads from the secret
master_user_secret_arn names, the grant's persistent argument, so every
removal places the drop, a retry included. On mongodb the destroy anchor
resolves the grant's input-variable set. The same administrator key arguments
as create select the values passed plainly in the drop order's env. Missing
selected values fail loud. Then delete_resources_by_time removes the
access_grant row and the permanent SSM password parameter with its secret row.
delete_schedules removes the schedules, and the final callback removes the
project's SaaS traces. The drop precedes generic deletion.

With keep_database_user true (a removal whose drop cannot log on) no drop
order is placed: the database user stays, and the run logs a warning naming
it; the rest of the removal runs as usual.

Names follow the CON-11 contract (ops work-log
2026-09-24/con-11-access-requests/contract.md, sections 1 and 2b).
"""

import json

# The input-variable key arguments and their MongoDB host env names.
ADMIN_CREDENTIALS = {
    "db_admin_user": "DB_ADMIN_USER",
    "db_admin_password": "DB_ADMIN_PASSWORD",
}

# The engines of an RDS database: the script reads its admin login from the
# secret master_user_secret_arn names.
RDS_ENGINES = ("postgres", "mysql")


def _drop_user(stack, db_user, admin_env):
    """Drop the user on the grant's host, then wait before generic deletion."""
    env_vars = {
        "METHOD": "destroy",
        "DB_ENGINE": stack.db_engine,
        "DB_ENDPOINT": stack.db_endpoint,
        "DB_PORT": stack.db_port,
        "DB_NAME": stack.db_name,
        "DB_LEVEL": stack.level,
        "DB_USER": db_user,
        **admin_env,
    }

    stack.add_groups_to_host(display=True,
                             human_description=f"Drop database user {db_user} on {stack.db_endpoint}",
                             env_vars=json.dumps(env_vars),
                             hostname=stack.host,
                             install_name=stack.install_name,
                             groups=stack.db_user_group)

    stack.wait_all()


def _drop_user_on_rds(stack, db_user):
    """An RDS database: the drop logs on with the login in the secret
    master_user_secret_arn names."""
    if not stack.get_attr("master_user_secret_arn"):
        raise ValueError(f"master_user_secret_arn is missing from the grant's arguments: "
                         f"database user {db_user} stays on {stack.db_endpoint}; only a "
                         f"removal with keep_database_user can leave it")
    _drop_user(stack, db_user, {"DB_MASTER_USER_SECRET_ARN": stack.master_user_secret_arn})


# DUP-128ad001: twin in aws/stacks/_config0_configs/db_password_access/_files/run.py
def _admin_credential(stack, key):
    """The value the argument ``key`` selects from the grant project's
    resolved input variables. The error never echoes the argument: a literal
    credential passed by mistake stays out of the log."""
    value = stack.inputvars.get(stack.get_attr(key))
    if not value:
        raise ValueError(f"{key} names no key of the grant project's input variables")
    return value


def _drop_user_on_mongodb(stack, db_user):
    # DUP-128ad002: twin in aws/stacks/_config0_configs/db_password_access/_files/run.py
    admin_env = {env_name: _admin_credential(stack, key) for key, env_name in ADMIN_CREDENTIALS.items()}
    _drop_user(stack, db_user, admin_env)


def run(stackargs):

    stack = newStack(stackargs)

    # The generic callback_delete arguments.
    stack.parse.add_required(key="parallel_ids",
                             default="null")

    stack.parse.add_required(key="sequential_ids",
                             default="null")

    stack.parse.add_required(key="keep_resources",
                             default="null")

    stack.parse.add_optional(key="parallel",
                             default="true")

    # A removal whose drop cannot log on (a wrong or changed admin password)
    # passes keep_database_user: no drop order, and the user stays.
    stack.parse.add_optional(key="keep_database_user",
                             types="bool",
                             default="false")

    # The grant's persistent arguments the drop needs.
    stack.parse.add_required(key="grant_id",
                             types="str")

    stack.parse.add_required(key="level",
                             types="str",
                             choices=["read", "read_write"])

    stack.parse.add_required(key="db_engine",
                             types="str",
                             choices=["mongodb", "postgres", "mysql"])

    stack.parse.add_required(key="db_endpoint",
                             types="str")

    stack.parse.add_required(key="db_port",
                             types="str")

    stack.parse.add_required(key="db_name",
                             types="str")

    stack.parse.add_required(key="host",
                             types="str")

    stack.parse.add_required(key="install_name",
                             types="str")

    # mongodb: the same input-variable key names the create stack takes.
    stack.parse.add_optional(key="db_admin_user",
                             types="str",
                             default=None)

    stack.parse.add_optional(key="db_admin_password",
                             types="str",
                             default=None)

    # postgres and mysql: the secret that holds the database's admin login.
    # Read only by a removal that drops the user.
    stack.parse.add_optional(key="master_user_secret_arn",
                             types="str",
                             default=None)

    stack.add_hostgroups("config0-hub:::aws::db-password-access-user",
                         "db_user_group")

    stack.add_substack("config0-hub:::config0_core::delete_schedules")
    stack.add_substack("config0-hub:::config0_core::delete_resources_by_time")

    stack.init_variables()
    stack.init_hostgroups()
    stack.init_substacks()

    if len(stack.parallel_ids) != 1:
        raise ValueError(f"parallel_ids must name the one grant schedule, got {stack.parallel_ids}")
    db_user = f"c0_{stack.grant_id[:16]}"

    if stack.keep_database_user:
        stack.logger.warning(f"keep_database_user: database user {db_user} stays on "
                             f"{stack.db_endpoint}; no drop order is placed")
    elif stack.db_engine in RDS_ENGINES:
        _drop_user_on_rds(stack, db_user)
    else:
        _drop_user_on_mongodb(stack, db_user)

    # From here on, callback_delete's chain.
    ref_schedule_ids = stack.parallel_ids[:]
    ref_schedule_ids.extend(stack.sequential_ids[:])

    input_values = {
        "ref_schedule_ids": ref_schedule_ids
    }

    if stack.get_attr("keep_resources"):
        input_values["keep_resources"] = stack.keep_resources

    if stack.get_attr("parallel") not in ["None", "null", None, False, "false"]:
        input_values["parallel_overide"] = True

    stack.delete_resources_by_time.insert(display=None,
                                          input_values=input_values)

    stack.wait_all()

    input_values = {}

    if stack.get_attr("parallel_ids"):
        input_values["parallel_ids"] = stack.parallel_ids

    if stack.get_attr("sequential_ids"):
        input_values["sequential_ids"] = stack.sequential_ids

    if stack.get_attr("parallel") not in ["None", "null", None, False, "false"]:
        input_values["parallel_overide"] = True

    stack.delete_schedules.insert(display=None,
                                  input_values=input_values,
                                  automation_phase="destroying_schedules",
                                  human_description="Delete schedules stack")

    stack.wait_all()

    stack.add_project_delete_callback()

    return stack.get_results()
