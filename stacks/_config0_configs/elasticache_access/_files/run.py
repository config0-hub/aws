"""ElastiCache access grant: one IAM role for one grantee on one cache.

One grant is one internal project, c0-access-<grant id>, and this stack runs
once for it. The elasticache-access execgroup creates the role
config0-access-<grant id>, trusted by config0-executor-remote for the grantee
only until end_time, with one inline policy for elasticache:Connect, and one
IAM-authenticated ElastiCache user c0-<first 16 hex of the grant id> in the
cache's existing user group, with the level's access string. The tf_executor write-back
records the access_grant row after a successful apply, so the row's existence
proves the role exists. Names and row fields follow the CON-11 contract (ops
work-log 2026-09-24/con-11-access-requests/contract.md, section 2b). The
project destroy removes the role and the user; nothing here deletes one.
"""

from datetime import datetime
import re

from config0_publisher.terraform import TFConstructor

TARGET_KIND = "elasticache"

GRANT_ID_RE = re.compile(r"^[0-9a-f]{32}\Z")

# The AWS name rule of the target id this stack puts in the IAM policy; saas-api
# refuses the same shapes (AccessRequestCreate), so a typed "*" or an ARN
# fragment never widens the grant past the one target.
# ReplicationGroupId: 1 to 40 letters, digits or hyphens, a letter first, no
# trailing hyphen, no two hyphens in a row; CreateServerlessCache states no rule
# for its name, so the same rule holds for both cache types. The user group id
# pattern is CreateReplicationGroup's UserGroupIds.member, [a-zA-Z][a-zA-Z0-9\-]*;
# CreateUserGroup states none
# (https://docs.aws.amazon.com/AmazonElastiCache/latest/APIReference/API_CreateReplicationGroup.html).
CACHE_NAME_RE = re.compile(r"^(?=.{1,40}\Z)[A-Za-z](?:-?[A-Za-z0-9])*\Z")
USER_GROUP_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*\Z")

END_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _check_grant(stack):
    if not GRANT_ID_RE.match(stack.grant_id):
        raise ValueError(f'grant_id must be 32 lowercase hex, got "{stack.grant_id}"')
    # UTC ISO 8601, second precision, Z suffix; strptime raises on anything else.
    datetime.strptime(stack.end_time, END_TIME_FORMAT)
    if not CACHE_NAME_RE.match(stack.cache_name):
        raise ValueError(f'cache_name must be an ElastiCache cache name, got "{stack.cache_name}"')
    if not USER_GROUP_ID_RE.match(stack.user_group_id):
        raise ValueError(f'user_group_id must be an ElastiCache user group id, got '
                         f'"{stack.user_group_id}"')


def run(stackargs):

    stack = newStack(stackargs)

    stack.parse.add_required(key="grant_id",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="grantee_owner_id",
                             tags="tfvar",
                             types="str")

    # level -> statements and access string; the elasticache-access
    # execgroup's access_policy module carries both per level.
    stack.parse.add_required(key="level",
                             tags="tfvar",
                             types="str",
                             choices=["read", "read_write"])

    stack.parse.add_required(key="end_time",
                             tags="tfvar",
                             types="str")

    # replication group id or serverless cache name
    stack.parse.add_required(key="cache_name",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="cache_type",
                             tags="tfvar",
                             types="str",
                             choices=["replication_group", "serverless"])

    stack.parse.add_required(key="user_group_id",
                             tags="tfvar",
                             types="str")

    stack.parse.add_required(key="engine",
                             tags="tfvar",
                             types="str",
                             choices=["redis", "valkey"])

    stack.parse.add_required(key="aws_default_region",
                             tags="tfvar,db,resource,tf_exec_env",
                             types="str")

    stack.parse.add_required(key="aws_account_id",
                             tags="tfvar",
                             types="str")

    stack.add_execgroup("config0-hub:::aws::elasticache-access",
                        "tf_execgroup")

    stack.add_substack("config0-hub:::config0_core::tf_executor")

    stack.init_variables()
    stack.init_execgroups()
    stack.init_substacks()

    _check_grant(stack)

    stack.set_variable("timeout", 600)

    stack.verify_variables()

    role_name = f"config0-access-{stack.grant_id}"
    # 19 characters, under CreateUser's 40 and inside its user id pattern (no
    # underscore); the elasticache-access execgroup's access_policy module
    # derives the same name.
    cache_user_id = f"c0-{stack.grant_id[:16]}"

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
        "target_name": stack.cache_name,
        "cache_name": stack.cache_name,
        "cache_type": stack.cache_type,
        "user_group_id": stack.user_group_id,
        "cache_user_id": cache_user_id,
        "aws_account_id": stack.aws_account_id,
        "region": stack.aws_default_region,
        "stack_fqn": stack.stackargs["stack"],
    })

    stack.tf_executor.insert(display=True,
                             **tf.get())

    return stack.get_results()
