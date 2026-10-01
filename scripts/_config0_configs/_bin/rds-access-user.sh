#!/bin/bash
#
# rds-access-user.sh - create or drop one CON-11 access grant's database user
# on an RDS or Aurora database (PostgreSQL, MySQL or MariaDB), authenticated
# by IAM. The rds-access-user script group runs it on a host in the
# database's VPC: the rds_access stack with METHOD=create, before the grant's
# IAM role exists, and the rds_access_destroy stack with METHOD=destroy,
# before the role is removed. Names follow the CON-11 contract (ops work-log
# 2026-09-24/con-11-access-requests/contract.md, section 2b).
#
# Environment:
#   METHOD             create or destroy
#   DB_ENGINE          postgres, mysql or mariadb
#   DB_ENDPOINT        the instance or cluster endpoint
#   DB_PORT            the endpoint's port
#   DB_NAME            the database the level's privileges apply to
#   DB_LEVEL           connect, read_only or read_write
#   DB_USER            the grant's database user, c0_<16 hex of the grant id>
#   DB_ADMIN_USER      the admin user; a secret, never printed
#   DB_ADMIN_PASSWORD  the admin password; a secret, never printed
#
# Sources:
#   "Creating a database account using IAM authentication",
#   https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.DBAccounts.html
#   (MariaDB and MySQL: CREATE USER ... IDENTIFIED WITH AWSAuthenticationPlugin
#   AS 'RDS'; PostgreSQL: create the user, then GRANT rds_iam; "If you remove
#   a user that is mapped to a database account, you should also remove the
#   database account with the DROP USER statement")
#   "Using SSL/TLS to encrypt a connection to a DB instance or cluster",
#   https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html
#   (the global-bundle.pem trust bundle for any commercial Region)
#
# Idempotent: create keeps an existing user and re-applies its grants; destroy
# treats a missing user as done. No engine expires the user: the grant's IAM
# trust end time is the only cutoff, and the user is dropped only when the
# grant is removed. Any failure exits non-zero.

set -euo pipefail

CA_BUNDLE_URL="https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem"

fail() {
    echo "rds-access-user: $*" >&2
    exit 1
}

for name in METHOD DB_ENGINE DB_ENDPOINT DB_PORT DB_NAME DB_LEVEL DB_USER DB_ADMIN_USER DB_ADMIN_PASSWORD; do
    [[ -n "${!name:-}" ]] || fail "$name is required"
done

case "$METHOD" in
    create|destroy) ;;
    *) fail "METHOD must be create or destroy, got $METHOD" ;;
esac

# The user name goes into SQL unquoted by the engine's own rules, so it is
# checked against the one shape the stack derives.
[[ "$DB_USER" =~ ^c0_[0-9a-f]{16}$ ]] || fail "DB_USER must be c0_<16 lowercase hex>, got $DB_USER"
[[ "$DB_PORT" =~ ^[0-9]+$ ]] || fail "DB_PORT must be a number, got $DB_PORT"
# MySQL and MariaDB read % in a GRANT's database name as "any characters", so
# a grant on it would reach every database; the stack refuses it too.
[[ "$DB_NAME" != *%* ]] || fail "DB_NAME must not contain %, got $DB_NAME"

# connect grants nothing beyond log on.
case "$DB_LEVEL" in
    connect) privileges="" ;;
    read_only) privileges="SELECT" ;;
    read_write) privileges="SELECT, INSERT, UPDATE, DELETE" ;;
    *) fail "DB_LEVEL must be connect, read_only or read_write, got $DB_LEVEL" ;;
esac

install_client() {
    local command_name="$1" package="$2"
    command -v "$command_name" >/dev/null && return 0
    command -v apt-get >/dev/null || fail "$command_name is missing and this host has no apt-get to install $package"
    apt-get -o DPkg::Lock::Timeout=600 update -y
    DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=600 install -y "$package"
}

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT
ca_file="$workdir/global-bundle.pem"

psql_admin() {
    PGHOST="$DB_ENDPOINT" PGPORT="$DB_PORT" PGDATABASE="$DB_NAME" \
        PGUSER="$DB_ADMIN_USER" PGPASSWORD="$DB_ADMIN_PASSWORD" \
        PGSSLMODE=verify-full PGSSLROOTCERT="$ca_file" PGCONNECT_TIMEOUT=30 \
        psql --no-psqlrc --quiet -v ON_ERROR_STOP=1 -v u="$DB_USER" -v db="$DB_NAME"
}

mysql_admin() {
    MYSQL_PWD="$DB_ADMIN_PASSWORD" mysql --no-defaults --protocol=TCP \
        --host="$DB_ENDPOINT" --port="$DB_PORT" --user="$DB_ADMIN_USER" \
        --ssl-mode=VERIFY_IDENTITY --ssl-ca="$ca_file" --connect-timeout=30 --batch
}

postgres_create() {
    {
        cat <<'SQL'
SELECT NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'u') AS absent \gset
\if :absent
CREATE ROLE :"u" LOGIN;
\endif
GRANT rds_iam TO :"u";
SQL
        if [[ -n "$privileges" ]]; then
            cat <<'SQL'
GRANT CONNECT ON DATABASE :"db" TO :"u";
GRANT USAGE ON SCHEMA public TO :"u";
SQL
            echo "GRANT $privileges ON ALL TABLES IN SCHEMA public TO :\"u\";"
            echo "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT $privileges ON TABLES TO :\"u\";"
        fi
        # An INSERT into a serial or bigserial key calls nextval(), which needs
        # USAGE on the sequence.
        if [[ "$DB_LEVEL" == read_write ]]; then
            cat <<'SQL'
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO :"u";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO :"u";
SQL
        fi
    } | psql_admin
}

# Revokes exactly what postgres_create granted, then drops the role. Nothing
# here drops an object: a role that still owns one fails DROP ROLE loud.
postgres_destroy() {
    psql_admin <<'SQL'
SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'u') AS present \gset
\if :present
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM :"u";
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM :"u";
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM :"u";
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM :"u";
REVOKE USAGE ON SCHEMA public FROM :"u";
REVOKE CONNECT ON DATABASE :"db" FROM :"u";
DROP ROLE :"u";
\endif
SQL
}

# A GRANT's database name is a pattern: _ matches any one character and %
# any run, so a grant on app_db would also reach appXdb. Each is
# backslash-escaped, the backslash itself first, before the name is quoted.
mysql_create() {
    local name="${DB_NAME//\\/\\\\}"
    name="${name//_/\\_}"
    name="${name//%/\\%}"
    local database="\`${name//\`/\`\`}\`"
    {
        echo "CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED WITH AWSAuthenticationPlugin AS 'RDS';"
        if [[ -n "$privileges" ]]; then
            echo "GRANT $privileges ON $database.* TO '$DB_USER'@'%';"
        fi
    } | mysql_admin
}

mysql_destroy() {
    echo "DROP USER IF EXISTS '$DB_USER'@'%';" | mysql_admin
}

case "$DB_ENGINE" in
    postgres) install_client psql postgresql-client ;;
    mysql|mariadb) install_client mysql mysql-client ;;
    *) fail "DB_ENGINE must be postgres, mysql or mariadb, got $DB_ENGINE" ;;
esac

curl -fsS --retry 3 -o "$ca_file" "$CA_BUNDLE_URL"

case "$DB_ENGINE" in
    postgres) "postgres_$METHOD" ;;
    mysql|mariadb) "mysql_$METHOD" ;;
esac

echo "rds-access-user: $METHOD of $DB_USER on $DB_ENDPOINT:$DB_PORT/$DB_NAME done"
