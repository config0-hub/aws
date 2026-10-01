"""Database password access grant: one temporary database user with a
generated password for one grantee, on an engine with no IAM authentication.

One grant is one internal project, c0-access-<grant id>, and this stack runs
once for it, in two jobs. The create job generates the password, seals it as
this schedule's secret row with an SSM copy that expires at end_time, and runs
the db-password-access-user script group on an existing host in the
database's VPC, through the ssm_ec2_exec install install_name selects. The
script creates the user c0_<first 16 hex of the grant id> with that password
and the level's grants on db_name. On the create job's success, the record
job writes the access_grant row, so the row's existence proves the user
exists. There is no IAM role and no Terraform: nothing in AWS is created, so
the row is record-only, written on the on_success edge as the
ssm_ec2_exec_eventbridge_install add-on writes its addon row. QHost's
access-session reads the password back through the hub's ssm_read for the
grantee.

The admin credentials arrive as input-variable selectors, never literals:
db_admin_user and db_admin_password each name a key of the grant project's
resolved input variables. The stack seals both values as this schedule's
record-only secret rows, and the host order reads them and the password by
secret:::<name>, so no order row or log carries a credential.

Names and row fields follow the CON-11 contract (ops work-log
2026-09-24/con-11-access-requests/contract.md, section 2b). No engine expires
the user: once end_time passes QHost refuses to hand the password out, and
the user is dropped only when the grant is removed, by
db_password_access_destroy on the same host; nothing here deletes one.
"""

from datetime import UTC, datetime
import json
import math
import re
import secrets
import string

TARGET_KIND = "db_password"

GRANT_ID_RE = re.compile(r"^[0-9a-f]{32}\Z")
END_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# The admin credential arguments and the secret each is sealed as.
ADMIN_CREDENTIALS = {
    "db_admin_user": "DB_ADMIN_USER",
    "db_admin_password": "DB_ADMIN_PASSWORD",
}

# The grant user's password: the secret it is sealed as, its length, and
# its alphabet, the [a-z0-9] the db-password-access-user script checks.
PASSWORD_SECRET = "db_password"
PASSWORD_SIZE = 32
PASSWORD_ALPHABET = string.ascii_lowercase + string.digits


def _check_grant(stack):
    if not GRANT_ID_RE.match(stack.grant_id):
        raise ValueError(f'grant_id must be 32 lowercase hex, got "{stack.grant_id}"')
    # UTC ISO 8601, second precision, Z suffix; strptime raises on anything else.
    datetime.strptime(stack.end_time, END_TIME_FORMAT)
    # MySQL and MariaDB read % in a GRANT's database name as "any characters":
    # a grant on it would reach every database on the instance.
    if "%" in stack.db_name:
        raise ValueError(f'db_name must not contain "%", got "{stack.db_name}"')


def _minutes_until(end_time):
    """Whole minutes from now until end_time, rounded up, so the stored copy
    of the password expires with the grant. add_secret refuses a value that is
    not positive: a grant already ended stores nothing."""
    end = datetime.strptime(end_time, END_TIME_FORMAT).replace(tzinfo=UTC)
    return math.ceil((end - datetime.now(UTC)).total_seconds() / 60)


def _admin_credential(stack, key):
    """The value the argument ``key`` selects from the grant project's
    resolved input variables. The error never echoes the argument: a literal
    credential passed by mistake stays out of the log."""
    value = stack.inputvars.get(stack.get_attr(key))
    if not value:
        raise ValueError(f"{key} names no key of the grant project's input variables")
    return value


def _draw_password():
    """The grant user's password, drawn with secrets: it is a credential,
    not an id, so it does not come from stack.random_id."""
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(PASSWORD_SIZE))


def _db_user(stack):
    """c0_ and the first 16 hex of the grant id, 19 characters, inside
    MySQL's 32; also a valid PostgreSQL and MongoDB user name."""
    return f"c0_{stack.grant_id[:16]}"


class Main(newSchedStack):

    def __init__(self, stackargs):
        newSchedStack.__init__(self, stackargs)

        self.parse.add_required(key="grant_id",
                                types="str")

        self.parse.add_required(key="grantee_owner_id",
                                types="str")

        # level -> the user's grants on db_name: read or read_write.
        self.parse.add_required(key="level",
                                types="str",
                                choices=["read", "read_write"])

        self.parse.add_required(key="end_time",
                                types="str")

        self.parse.add_required(key="db_engine",
                                types="str",
                                choices=["mongodb", "postgres", "mysql"])

        self.parse.add_required(key="db_endpoint",
                                types="str")

        self.parse.add_required(key="db_port",
                                types="str")

        self.parse.add_required(key="db_name",
                                types="str")

        # hostname of the server record in the VPC the script runs on
        self.parse.add_required(key="host",
                                types="str")

        # selects the ssm_ec2_exec_eventbridge install the host order runs
        # through, and the install whose KMS key seals the secrets
        self.parse.add_required(key="install_name",
                                types="str")

        self.parse.add_required(key="db_admin_user",
                                types="str")

        self.parse.add_required(key="db_admin_password",
                                types="str")

        self.parse.add_required(key="aws_default_region",
                                types="str")

        self.parse.add_required(key="aws_account_id",
                                types="str")

        self.stack.add_hostgroups("config0-hub:::aws::db-password-access-user",
                                  "db_user_group")

        self.stack.init_hostgroups()

    def run_create(self):
        stack = self.stack

        stack.init_variables()

        _check_grant(stack)

        stack.set_variable("timeout", 600)

        stack.verify_variables()

        db_user = _db_user(stack)

        # Record-only secret rows; the host order reads them back. No SSM copy.
        for key in ADMIN_CREDENTIALS:
            stack.add_secret(name=key,
                             value=_admin_credential(stack, key),
                             insert_ssm=False)

        # The grantee's password: the secret row the host order reads, and
        # the SSM copy QHost reads back for the grantee, gone at end_time.
        stack.add_secret(name=PASSWORD_SECRET,
                         value=_draw_password(),
                         expire_mins=_minutes_until(stack.end_time))

        env_vars = {
            "METHOD": "create",
            "DB_ENGINE": stack.db_engine,
            "DB_ENDPOINT": stack.db_endpoint,
            "DB_PORT": stack.db_port,
            "DB_NAME": stack.db_name,
            "DB_LEVEL": stack.level,
            "DB_USER": db_user,
            "DB_PASSWORD": f"secret:::{PASSWORD_SECRET}",
        }
        for key, env_name in ADMIN_CREDENTIALS.items():
            env_vars[env_name] = f"secret:::{key}"

        stack.add_groups_to_host(display=True,
                                 human_description=f"Create database user {db_user} on {stack.db_endpoint}",
                                 env_vars=json.dumps(env_vars),
                                 hostname=stack.host,
                                 install_name=stack.install_name,
                                 groups=stack.db_user_group)

        # The host order's child runs the script; the job settles only after
        # it, so the record job's on_success edge follows the script.
        return stack.wait_all()

    def run_record(self):
        stack = self.stack

        stack.init_variables()

        _check_grant(stack)

        stack.verify_variables()

        # name is the role name rule of every other kind, so the row's _id is
        # the one QHost's access-session reads by primary key, although this
        # kind has no role.
        return stack.record_resource(values={
            "resource_type": "access_grant",
            "provider": "aws",
            "name": f"config0-access-{stack.grant_id}",
            "grant_id": stack.grant_id,
            "grantee_owner_id": stack.grantee_owner_id,
            "level": stack.level,
            "end_time": stack.end_time,
            "target_kind": TARGET_KIND,
            "target_name": stack.db_endpoint,
            "db_engine": stack.db_engine,
            "db_endpoint": stack.db_endpoint,
            "db_port": stack.db_port,
            "db_name": stack.db_name,
            "host": stack.host,
            "install_name": stack.install_name,
            "db_user": _db_user(stack),
            "aws_account_id": stack.aws_account_id,
            "region": stack.aws_default_region,
            "stack_fqn": stack.stackargs["stack"],
        })

    def run(self):
        self.add_job("create")
        self.add_job("record")

        return self.finalize_jobs()

    def schedule(self):
        # The row is written only on the create job's success.
        sched = self.new_schedule()
        sched.job = "create"
        sched.archive.timeout = 1800
        sched.archive.timewait = 120
        sched.human_description = "Create the grant's database user"
        sched.on_success = ["record"]
        self.add_schedule()

        sched = self.new_schedule()
        sched.job = "record"
        sched.archive.timeout = 600
        sched.archive.timewait = 30
        sched.human_description = "Record the access grant"
        self.add_schedule()

        return self.get_schedules()
