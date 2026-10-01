#!/bin/bash
#
# docdb-access-user.sh - create or drop one CON-11 access grant's DocumentDB
# user: the $external user whose name is the grant role's ARN, authenticated
# by MONGODB-AWS. The docdb-access-user script group runs it on a host in the
# cluster's VPC: the docdb_access stack with METHOD=create, before the grant's
# IAM role exists, and the docdb_access_destroy stack with METHOD=destroy,
# before the role is removed. Names follow the CON-11 contract (ops work-log
# 2026-09-24/con-11-access-requests/contract.md, section 2b).
#
# Environment:
#   METHOD             create or destroy
#   DB_ENDPOINT        the cluster endpoint
#   DB_PORT            the endpoint's port
#   DB_NAME            the database the level's role applies to
#   DB_LEVEL           read or read_write
#   DB_USER            the grant role's ARN, arn:aws:iam::<account>:role/config0-access-<grant id>
#   DB_ADMIN_USER      the primary user; a secret, never printed
#   DB_ADMIN_PASSWORD  the primary user's password; a secret, never printed
#
# Sources:
#   "Authentication using IAM identity" (Amazon DocumentDB),
#   https://docs.aws.amazon.com/documentdb/latest/developerguide/iam-identity-auth.html
#   (instance-based clusters 5.0; connect as the primary user, then in
#   $external db.createUser({user: <role ARN>, mechanisms: ["MONGODB-AWS"],
#   roles: [...]}); db.dropUser(<role ARN>) drops it)
#   "Connecting programmatically to Amazon DocumentDB",
#   https://docs.aws.amazon.com/documentdb/latest/developerguide/connect_programmatically.html
#   (the global-bundle.pem CA file; tls=true, replicaSet=rs0, retryWrites=false)
#
# Idempotent: create sets the level's role on an existing user; destroy treats
# a missing user as done. No engine expires the user: the grant's IAM trust end
# time is the only cutoff, and the user is dropped only when the grant is
# removed. Any failure exits non-zero.

set -euo pipefail

CA_BUNDLE_URL="https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem"
# The MongoDB apt repository the mongodb repo's ubuntu_vendor_setup uses.
MONGODB_REPO_VERSION="8.0"

fail() {
    echo "docdb-access-user: $*" >&2
    exit 1
}

for name in METHOD DB_ENDPOINT DB_PORT DB_NAME DB_LEVEL DB_USER DB_ADMIN_USER DB_ADMIN_PASSWORD; do
    [[ -n "${!name:-}" ]] || fail "$name is required"
done

case "$METHOD" in
    create|destroy) ;;
    *) fail "METHOD must be create or destroy, got $METHOD" ;;
esac

[[ "$DB_USER" =~ ^arn:aws:iam::[0-9]{12}:role/config0-access-[0-9a-f]{32}$ ]] \
    || fail "DB_USER must be a grant role ARN, got $DB_USER"
[[ "$DB_PORT" =~ ^[0-9]+$ ]] || fail "DB_PORT must be a number, got $DB_PORT"

case "$DB_LEVEL" in
    read) DB_ROLE="read" ;;
    read_write) DB_ROLE="readWrite" ;;
    *) fail "DB_LEVEL must be read or read_write, got $DB_LEVEL" ;;
esac

install_mongosh() {
    command -v mongosh >/dev/null && return 0
    command -v apt-get >/dev/null || fail "mongosh is missing and this host has no apt-get to install it"
    local keyring="/usr/share/keyrings/mongodb-server-$MONGODB_REPO_VERSION.gpg"
    local codename
    codename="$(sed -n 's/^VERSION_CODENAME=//p' /etc/os-release)"
    [[ -n "$codename" ]] || fail "no VERSION_CODENAME in /etc/os-release"
    curl -fsSL "https://www.mongodb.org/static/pgp/server-$MONGODB_REPO_VERSION.asc" | gpg --dearmor > "$keyring"
    chmod 0644 "$keyring"
    echo "deb [ arch=amd64,arm64 signed-by=$keyring ] https://repo.mongodb.org/apt/ubuntu $codename/mongodb-org/$MONGODB_REPO_VERSION multiverse" \
        > "/etc/apt/sources.list.d/mongodb-org-$MONGODB_REPO_VERSION.list"
    apt-get -o DPkg::Lock::Timeout=600 update -y
    DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=600 install -y mongodb-mongosh
}

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
CA_FILE="$workdir/global-bundle.pem"

install_mongosh
curl -fsS --retry 3 -o "$CA_FILE" "$CA_BUNDLE_URL"

export METHOD DB_ENDPOINT DB_PORT DB_NAME DB_USER DB_ROLE DB_ADMIN_USER DB_ADMIN_PASSWORD CA_FILE

# The script reads every value from the environment, so the credentials never
# reach the command line. An uncaught error exits mongosh non-zero.
# shellcheck disable=SC2016  # $external is DocumentDB's database name, not a shell variable
mongosh --nodb --norc --quiet --eval '
const env = process.env;
const uri = "mongodb://" + encodeURIComponent(env.DB_ADMIN_USER) + ":" + encodeURIComponent(env.DB_ADMIN_PASSWORD)
    + "@" + env.DB_ENDPOINT + ":" + env.DB_PORT
    + "/?tls=true&tlsCAFile=" + env.CA_FILE + "&replicaSet=rs0&retryWrites=false&serverSelectionTimeoutMS=30000";
const external = new Mongo(uri).getDB("$external");
const roles = [{ role: env.DB_ROLE, db: env.DB_NAME }];
const existing = external.getUser(env.DB_USER);
if (env.METHOD === "create") {
    if (existing === null) {
        external.createUser({ user: env.DB_USER, mechanisms: ["MONGODB-AWS"], roles: roles });
    } else {
        external.updateUser(env.DB_USER, { roles: roles });
    }
} else if (existing !== null) {
    external.dropUser(env.DB_USER);
}
'

echo "docdb-access-user: $METHOD of $DB_USER on $DB_ENDPOINT:$DB_PORT/$DB_NAME done"
