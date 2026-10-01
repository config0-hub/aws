#!/bin/bash
#
# db-password-access-user.sh - create or drop one CON-11 access grant's
# database user with a password, on an engine with no IAM authentication:
# MongoDB (the mongodb repo's replica set on EC2), or an RDS or Aurora
# PostgreSQL or MySQL database with IAM authentication off. The
# db-password-access-user script group runs it on a host in the database's
# VPC: the db_password_access stack with METHOD=create, and the
# db_password_access_destroy stack with METHOD=destroy. Names follow the
# CON-11 contract (ops work-log 2026-09-24/con-11-access-requests/contract.md,
# section 2b).
#
# Environment:
#   METHOD             create or destroy
#   DB_ENGINE          mongodb, postgres or mysql
#   DB_ENDPOINT        the database endpoint (for mongodb, the primary's address)
#   DB_PORT            the endpoint's port
#   DB_NAME            the database the level's grants apply to
#   DB_LEVEL           read or read_write
#   DB_USER            the grant's database user, c0_<16 hex of the grant id>
#   DB_PASSWORD        create only: the grant user's password, 32 of [a-z0-9];
#                      a secret, never printed
#   DB_ADMIN_USER      the admin user; a secret, never printed
#   DB_ADMIN_PASSWORD  the admin password; a secret, never printed
#
# Sources:
#   "CREATE ROLE" and "ALTER ROLE" (PostgreSQL), PASSWORD 'password'
#   "CREATE USER Statement" and "ALTER USER Statement" (MySQL 8.0),
#   IDENTIFIED BY 'auth_string'
#   "db.createUser()", "db.updateUser()", "db.dropUser()" (MongoDB); the read
#   and readWrite built-in roles
#   "Using SSL/TLS to encrypt a connection to a DB instance or cluster",
#   https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html
#   (the global-bundle.pem trust bundle for any commercial Region)
#   The mongodb repo's replica set serves a self-signed certificate; its own
#   mongosh calls connect with --tlsAllowInvalidCertificates, and so does this.
#
# Idempotent: create keeps an existing user, resets its password and
# re-applies its grants, so a re-run's newly sealed password is the one that
# works; destroy treats a missing user as done. No engine expires the user:
# QHost stops handing the password out at the grant's end time, and the user
# is dropped only when the grant is removed. Any failure exits non-zero. The
# passwords go to the clients on stdin or in the environment, never on a
# command line.

set -euo pipefail

CA_BUNDLE_URL="https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem"
# The MongoDB apt repository the mongodb repo's ubuntu_vendor_setup uses.
MONGODB_REPO_VERSION="8.0"

fail() {
    echo "db-password-access-user: $*" >&2
    exit 1
}

for name in METHOD DB_ENGINE DB_ENDPOINT DB_PORT DB_NAME DB_LEVEL DB_USER DB_ADMIN_USER DB_ADMIN_PASSWORD; do
    [[ -n "${!name:-}" ]] || fail "$name is required"
done

case "$METHOD" in
    create)
        # The password goes into SQL quoted by this script, so it is checked
        # against the one shape the stack generates. The value is never echoed.
        [[ "${DB_PASSWORD:-}" =~ ^[a-z0-9]{32}$ ]] || fail "DB_PASSWORD must be 32 of [a-z0-9]"
        ;;
    destroy) ;;
    *) fail "METHOD must be create or destroy, got $METHOD" ;;
esac

# The user name goes into SQL unquoted by the engine's own rules, so it is
# checked against the one shape the stack derives.
[[ "$DB_USER" =~ ^c0_[0-9a-f]{16}$ ]] || fail "DB_USER must be c0_<16 lowercase hex>, got $DB_USER"
[[ "$DB_PORT" =~ ^[0-9]+$ ]] || fail "DB_PORT must be a number, got $DB_PORT"
# MySQL and MariaDB read % in a GRANT's database name as "any characters", so
# a grant on it would reach every database; the stack refuses it too.
[[ "$DB_NAME" != *%* ]] || fail "DB_NAME must not contain %, got $DB_NAME"

case "$DB_LEVEL" in
    read) privileges="SELECT"; mongodb_role="read" ;;
    read_write) privileges="SELECT, INSERT, UPDATE, DELETE"; mongodb_role="readWrite" ;;
    *) fail "DB_LEVEL must be read or read_write, got $DB_LEVEL" ;;
esac

install_client() {
    local command_name="$1" package="$2"
    command -v "$command_name" >/dev/null && return 0
    command -v apt-get >/dev/null || fail "$command_name is missing and this host has no apt-get to install $package"
    apt-get -o DPkg::Lock::Timeout=600 update -y
    DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=600 install -y "$package"
}

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
SQL
        echo "ALTER ROLE :\"u\" WITH LOGIN PASSWORD '$DB_PASSWORD';"
        cat <<'SQL'
GRANT CONNECT ON DATABASE :"db" TO :"u";
GRANT USAGE ON SCHEMA public TO :"u";
SQL
        echo "GRANT $privileges ON ALL TABLES IN SCHEMA public TO :\"u\";"
        echo "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT $privileges ON TABLES TO :\"u\";"
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
        echo "CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASSWORD';"
        echo "ALTER USER '$DB_USER'@'%' IDENTIFIED BY '$DB_PASSWORD';"
        echo "GRANT $privileges ON $database.* TO '$DB_USER'@'%';"
    } | mysql_admin
}

mysql_destroy() {
    echo "DROP USER IF EXISTS '$DB_USER'@'%';" | mysql_admin
}

# The script reads every value from the environment, so the credentials never
# reach the command line. An uncaught error exits mongosh non-zero.
mongodb_run() {
    DB_ROLE="$mongodb_role" METHOD="$METHOD" DB_ENDPOINT="$DB_ENDPOINT" DB_PORT="$DB_PORT" \
        DB_NAME="$DB_NAME" DB_USER="$DB_USER" DB_PASSWORD="${DB_PASSWORD:-}" \
        DB_ADMIN_USER="$DB_ADMIN_USER" DB_ADMIN_PASSWORD="$DB_ADMIN_PASSWORD" \
        mongosh --nodb --norc --quiet --eval '
const env = process.env;
const uri = "mongodb://" + encodeURIComponent(env.DB_ADMIN_USER) + ":" + encodeURIComponent(env.DB_ADMIN_PASSWORD)
    + "@" + env.DB_ENDPOINT + ":" + env.DB_PORT
    + "/?tls=true&tlsAllowInvalidCertificates=true&authSource=admin&serverSelectionTimeoutMS=30000";
const target = new Mongo(uri).getDB(env.DB_NAME);
const roles = [{ role: env.DB_ROLE, db: env.DB_NAME }];
const existing = target.getUser(env.DB_USER);
if (env.METHOD === "create") {
    if (existing === null) {
        target.createUser({ user: env.DB_USER, pwd: env.DB_PASSWORD, roles: roles });
    } else {
        target.updateUser(env.DB_USER, { pwd: env.DB_PASSWORD, roles: roles });
    }
} else if (existing !== null) {
    target.dropUser(env.DB_USER);
}
'
}

case "$DB_ENGINE" in
    mongodb) install_mongosh ;;
    postgres) install_client psql postgresql-client ;;
    mysql) install_client mysql mysql-client ;;
    *) fail "DB_ENGINE must be mongodb, postgres or mysql, got $DB_ENGINE" ;;
esac

case "$DB_ENGINE" in
    mongodb) mongodb_run ;;
    postgres|mysql)
        curl -fsS --retry 3 -o "$ca_file" "$CA_BUNDLE_URL"
        "${DB_ENGINE}_$METHOD"
        ;;
esac

echo "db-password-access-user: $METHOD of $DB_USER on $DB_ENDPOINT:$DB_PORT/$DB_NAME done"
