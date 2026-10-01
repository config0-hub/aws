"""Remove an RDS access grant: the destroy INSTRUCTION of an rds grant project.

The grant project's destroy anchor runs this stack (saas-api
``ACCESS_DESTROY_STACKS``) with the grant's persistent arguments plus the
generic callback_delete ones: parallel_ids names the one grant schedule. A
host order has no destroy of its own, so this stack first runs the
rds-access-user script group with METHOD=destroy on the same host, which drops
the grant's database user (a missing user is done). The admin credentials are
the grant run's own sealed secret rows, read through secret_refs by the grant
schedule id; the removal needs no input variables. When an admin row is
missing but the grant's access_grant row exists, the removal fails loud: that
row is written only after the create script ran, so a drop is owed. When the
access_grant row is absent too the drop is skipped: the create never reached
the host, or an earlier removal already dropped the user and deleted the
rows. Then, exactly as
callback_delete does, delete_resources_by_time removes the Terraform-backed
role and the access_grant row, delete_schedules removes the schedules, and the
final callback removes the project's SaaS traces. The drop runs first because
the generic delete also removes the secret rows it reads.

With keep_database_user true (a removal whose drop cannot log on) no drop
order is placed: the database user stays, and the run logs a warning naming
it; the rest of the removal runs as usual.

Names follow the CON-11 contract (ops work-log
2026-09-24/con-11-access-requests/contract.md, sections 1 and 2b).
"""

import json

# The admin credential secret rows the grant run sealed, and their env names.
ADMIN_CREDENTIALS = {
    "db_admin_user": "DB_ADMIN_USER",
    "db_admin_password": "DB_ADMIN_PASSWORD",
}


def _drop_user(stack, grant_schedule_id, db_user):
    """Run the script group with METHOD=destroy on the grant's host, reading
    the grant run's sealed admin secrets by the grant schedule id, and wait
    for it before the generic delete."""
    env_vars = {
        "METHOD": "destroy",
        "DB_ENGINE": stack.db_engine,
        "DB_ENDPOINT": stack.db_endpoint,
        "DB_PORT": stack.db_port,
        "DB_NAME": stack.db_name,
        "DB_LEVEL": stack.level,
        "DB_USER": db_user,
    }
    secret_refs = {}
    for key, env_name in ADMIN_CREDENTIALS.items():
        env_vars[env_name] = f"secret:::{key}"
        secret_refs[env_name] = {"name": key, "source": "resource", "schedule_id": grant_schedule_id}

    stack.add_groups_to_host(display=True,
                             human_description=f"Drop database user {db_user} on {stack.db_endpoint}",
                             env_vars=json.dumps(env_vars),
                             secret_refs=secret_refs,
                             hostname=stack.host,
                             install_name=stack.install_name,
                             groups=stack.db_user_group)

    stack.wait_all()


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
                             choices=["connect", "read_only", "read_write"])

    stack.parse.add_required(key="db_engine",
                             types="str",
                             choices=["postgres", "mysql", "mariadb"])

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

    stack.add_hostgroups("config0-hub:::aws::rds-access-user",
                         "db_user_group")

    stack.add_substack("config0-hub:::config0_core::delete_schedules")
    stack.add_substack("config0-hub:::config0_core::delete_resources_by_time")

    stack.init_variables()
    stack.init_hostgroups()
    stack.init_substacks()

    if len(stack.parallel_ids) != 1:
        raise ValueError(f"parallel_ids must name the one grant schedule, got {stack.parallel_ids}")
    (grant_schedule_id,) = stack.parallel_ids

    db_user = f"c0_{stack.grant_id[:16]}"

    if stack.keep_database_user:
        stack.logger.warning(f"keep_database_user: database user {db_user} stays on "
                             f"{stack.db_endpoint}; no drop order is placed")
    else:
        sealed = {row["name"] for row in stack.get_resource(resource_type="secret",
                                                            ref_schedule_id=grant_schedule_id,
                                                            overlay_tfstate=False)}
        missing = sorted(set(ADMIN_CREDENTIALS) - sealed)
        if not missing:
            _drop_user(stack, grant_schedule_id, db_user)
        elif stack.get_resource(resource_type="access_grant",
                                ref_schedule_id=grant_schedule_id,
                                overlay_tfstate=False):
            # The access_grant row is written only after the create script
            # ran, so a drop is owed and a missing admin row cannot skip it.
            raise ValueError(f"sealed admin secret row(s) {missing} missing on grant schedule "
                             f"{grant_schedule_id} while its access_grant row exists: database "
                             f"user {db_user} stays on {stack.db_endpoint}; only a removal with "
                             f"keep_database_user can leave it")
        # Neither an admin row nor the access_grant row: the create never
        # reached the host, or an earlier removal already dropped the user and
        # its generic delete took the rows, so a retry converges.

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

    return stack.get_results(None)
