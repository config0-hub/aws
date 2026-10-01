"""Redshift access grant: one IAM role for one grantee to log on to one database.

One grant is one internal project, c0-access-<grant id>, and this stack runs
once for it. The redshift-access execgroup creates the role
config0-access-<grant id>, trusted by config0-executor-remote for the grantee
only until end_time, with one inline policy for IAM database credentials on
the cluster's one database. No database user is created here: Redshift creates
it on the first GetClusterCredentials call with Autocreate=true, and it stays
the user's own. The tf_executor write-back records the access_grant row after
a successful apply, so the row's existence proves the role exists. Names and
row fields follow the CON-11 contract (ops work-log
2026-09-24/con-11-access-requests/contract.md, section 2b). The project
destroy removes the role; nothing here deletes one.
"""

from datetime import datetime
import re

from config0_publisher.terraform import TFConstructor

TARGET_KIND = "redshift"

# GetClusterCredentials DbUser: at most 64 characters. The redshift-access
# execgroup's access_policy module derives the same name.
DB_USER_MAX = 64

GRANT_ID_RE = re.compile(r"^[0-9a-f]{32}\Z")

# The AWS name rule of the target id this stack puts in the IAM policy; saas-api
# refuses the same shapes (AccessRequestCreate), so a typed "*" or an ARN
# fragment never widens the grant past the one target.
# Redshift ClusterIdentifier: 1 to 63 lowercase letters, digits or hyphens, a
# letter first, no trailing hyphen, no two hyphens in a row
# (https://docs.aws.amazon.com/redshift/latest/APIReference/API_CreateCluster.html).
REDSHIFT_CLUSTER_RE = re.compile(r"^(?=.{1,63}\Z)[a-z](?:-?[a-z0-9])*\Z")

# db_groups, the groups the user joins at log on: comma-separated names, each
# letters, digits and underscores (the CON-11 contract's rule); saas-api
# refuses the same shape. A "*" would allow JoinGroup on every group.
DB_GROUPS_RE = re.compile(r"^[A-Za-z0-9_]+(?:,[A-Za-z0-9_]+)*\Z")

END_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _check_grant(stack):
    if not GRANT_ID_RE.match(stack.grant_id):
        raise ValueError(f'grant_id must be 32 lowercase hex, got "{stack.grant_id}"')
    # UTC ISO 8601, second precision, Z suffix; strptime raises on anything else.
    datetime.strptime(stack.end_time, END_TIME_FORMAT)
    if not REDSHIFT_CLUSTER_RE.match(stack.redshift_cluster):
        raise ValueError(f'redshift_cluster must be a Redshift cluster identifier, got '
                         f'"{stack.redshift_cluster}"')
    # The default, an empty string, joins no group.
    if stack.db_groups and not DB_GROUPS_RE.match(stack.db_groups):
        raise ValueError(f'db_groups must be comma-separated group names of letters, digits '
                         f'or underscores, got "{stack.db_groups}"')


def run(stackargs):

    stack = newStack(stackargs)

    stack.parse.add_required(key="grant_id",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="grantee_owner_id",
                             tags="tfvar",
                             types="str")

    # level -> statements; the redshift-access execgroup's access_policy
    # module carries the statements per level.
    stack.parse.add_required(key="level",
                             tags="tfvar",
                             types="str",
                             choices=["connect"])

    stack.parse.add_required(key="end_time",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="redshift_cluster",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="db_name",
                             tags="tfvar",
                             types="str")

    # comma-separated; existing database groups the user joins at log on
    stack.parse.add_optional(key="db_groups",
                             types="str",
                             default="")

    stack.parse.add_required(key="aws_default_region",
                             tags="tfvar,db,resource,tf_exec_env",
                             types="str")

    stack.parse.add_required(key="aws_account_id",
                             tags="tfvar",
                             types="str")

    stack.add_execgroup("config0-hub:::aws::redshift-access",
                        "tf_execgroup")

    stack.add_substack("config0-hub:::config0_core::tf_executor")

    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    _check_grant(stack)

    stack.set_variable("db_group_names",
                       [group for group in stack.to_list(stack.db_groups) if group],
                       tags="tfvar",
                       types="list")

    stack.set_variable("timeout", 600)

    stack.verify_variables()

    role_name = f"config0-access-{stack.grant_id}"

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
        "target_name": stack.redshift_cluster,
        "redshift_cluster": stack.redshift_cluster,
        "db_name": stack.db_name,
        "db_groups": stack.db_groups,
        "db_user": role_name.lower()[:DB_USER_MAX],
        "aws_account_id": stack.aws_account_id,
        "region": stack.aws_default_region,
        "stack_fqn": stack.stackargs["stack"],
    })

    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()
