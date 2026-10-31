"""Create the migrator and runtime database roles. Safe to re-run.

Uses the current DATABASE_URL (or ADMIN_DATABASE_URL once set) as the admin login,
then rewrites .env so the app runs as creatoros_app. Passwords are never printed.
"""

import os
import secrets
import string
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql

MIGRATOR, APP = "creatoros_migrator", "creatoros_app"
ENV = Path(__file__).resolve().parents[3] / ".env"


def password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(40))


def with_login(url: str, user: str, pw: str) -> str:
    parts = urlsplit(url)
    host = parts.netloc.rsplit("@", 1)[1]
    return urlunsplit(parts._replace(netloc=f"{user}:{pw}@{host}"))


def plain(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://")


def main() -> None:
    lines = ENV.read_text(encoding="utf-8").splitlines()
    env = dict(line.split("=", 1) for line in lines if "=" in line and not line.startswith("#"))
    admin_url = env.get("ADMIN_DATABASE_URL") or env["DATABASE_URL"]
    if urlsplit(admin_url).username in (MIGRATOR, APP):
        sys.exit("expected an admin login in ADMIN_DATABASE_URL or DATABASE_URL")

    migrator_pw, app_pw = password(), password()
    i = sql.Identifier
    with psycopg.connect(plain(admin_url), autocommit=True) as c:
        database = c.execute("SELECT current_database()").fetchone()[0]
        for role, pw, attrs in (
            (MIGRATOR, migrator_pw, "LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB"),
            (APP, app_pw, "LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOBYPASSRLS"),
        ):
            exists = c.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
            verb = "ALTER" if exists else "CREATE"
            c.execute(
                sql.SQL(verb + " ROLE {} WITH " + attrs + " PASSWORD {}").format(i(role), sql.Literal(pw))
            )
        c.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(i(database), i(MIGRATOR)))
        c.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(i(database), i(APP)))
        c.execute(sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(i(MIGRATOR)))
        c.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(i(APP)))
        c.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM PUBLIC"))
        # The runtime role must never own tables: owners bypass row-level security.
        c.execute(sql.SQL("GRANT {} TO CURRENT_USER").format(i(MIGRATOR)))
        c.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
                "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
            ).format(i(MIGRATOR), i(APP))
        )

    new = {
        "ADMIN_DATABASE_URL": admin_url,
        "MIGRATION_DATABASE_URL": with_login(admin_url, MIGRATOR, migrator_pw),
        "DATABASE_URL": with_login(admin_url, APP, app_pw),
    }
    kept = [line for line in lines if line.split("=", 1)[0] not in new]
    tmp = ENV.with_suffix(".new")
    tmp.write_text("\n".join([f"{k}={v}" for k, v in new.items()] + kept) + "\n", encoding="utf-8")
    os.replace(tmp, ENV)
    print(f"roles ready: {MIGRATOR}, {APP}")


if __name__ == "__main__":
    main()
