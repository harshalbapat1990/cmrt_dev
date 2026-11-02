#!/usr/bin/env python3
import os
import sys
import argparse
from typing import List
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url, URL
from sqlalchemy.exc import SQLAlchemyError


def read_sql_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def split_batches_for_mssql(sql_text: str) -> List[str]:
    """Split on GO for SQL Server."""
    out: List[str] = []
    cur: List[str] = []
    for line in sql_text.splitlines():
        if line.strip().upper() == "GO":
            batch = "\n".join(cur).strip()
            if batch:
                out.append(batch)
            cur = []
        else:
            cur.append(line)
    final = "\n".join(cur).strip()
    if final:
        out.append(final)
    return out


def split_statements_semicolon(sql_text: str) -> List[str]:
    """
    Simple semicolon splitter for admin-stage SQL (DROP/CREATE DB).
    Assumes the file contains only plain DDL statements, not function bodies.
    """
    parts = sql_text.split(";")
    stmts = []
    for p in parts:
        s = p.strip()
        if not s:
            continue
        # Re-append the semicolon if you prefer, but not required by exec_driver_sql.
        stmts.append(s)
    return stmts


def build_admin_url(url: URL, backend: str) -> URL:
    if backend.startswith("postgresql"):
        return url.set(database="postgres")
    if backend.startswith("mssql"):
        return url.set(database="master")
    if backend.startswith("mysql"):
        return url.set(database="mysql")
    return url


def ensure_sync_driver(drivername: str):
    if "+asyncpg" in drivername or "async" in drivername:
        raise RuntimeError(
            "Async driver detected in DATABASE_URL. Use a sync URL, e.g. 'postgresql://user:pass@host/db'."
        )


def terminate_blockers_postgres(conn, db_name: str):
    conn.execute(
        text(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = :db
              AND pid <> pg_backend_pid();
            """
        ),
        {"db": db_name},
    )


def run_admin_sql(engine: Engine, admin_sql: str, backend: str, target_db: str | None, force: bool):
    """
    Execute admin SQL (DROP/CREATE DATABASE) with NO surrounding transaction.
    For Postgres: run one statement at a time on an AUTOCOMMIT connection.
    """
    # IMPORTANT: DO NOT use engine.begin() here.
    with engine.connect() as conn:
        # Make doubly sure autocommit is in effect on the connection:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")

        # Optional: terminate blockers on Postgres before DROP
        if backend.startswith("postgresql") and force and target_db:
            terminate_blockers_postgres(conn, target_db)

        if backend.startswith("mssql"):
            # SQL Server: split on GO
            batches = split_batches_for_mssql(admin_sql)
            for b in batches:
                if b.strip():
                    conn.exec_driver_sql(b)
        elif backend.startswith("postgresql") or backend.startswith("mysql"):
            # Postgres/MySQL admin: split into single statements and run one-by-one
            for stmt in split_statements_semicolon(admin_sql):
                conn.exec_driver_sql(stmt)
        else:
            # Fallback: try as-is (single statement or already compatible)
            s = admin_sql.strip()
            if s:
                conn.exec_driver_sql(s)


def run_schema_sql(engine: Engine, schema_sql: str, backend: str, timeout_sec: int | None):
    """
    Execute schema SQL (tables/schemas) WITH a transaction.
    """
    with engine.begin() as conn:
        if timeout_sec and backend.startswith("postgresql"):
            conn.exec_driver_sql(f"SET statement_timeout TO {int(timeout_sec) * 1000}")

        if backend.startswith("mssql"):
            batches = split_batches_for_mssql(schema_sql)
            for b in batches:
                if b.strip():
                    conn.exec_driver_sql(b)
        else:
            # For Postgres/MySQL, a single execute often works, but you can also split if preferred.
            # If your schema.sql contains function bodies with semicolons, avoid naive splitting here.
            conn.exec_driver_sql(schema_sql)


def main():
    parser = argparse.ArgumentParser(description="Two-stage SQL runner: admin then schema.")
    parser.add_argument("--admin-sql", required=True, help="SQL file for DROP/CREATE DATABASE")
    parser.add_argument("--schema-sql", required=True, help="SQL file for schemas/tables")
    parser.add_argument("--echo", action="store_true", help="Echo SQLAlchemy SQL")
    parser.add_argument("--timeout", type=int, default=180, help="Statement timeout (seconds) for schema stage on Postgres")
    parser.add_argument("--force", action="store_true", help="Terminate blocking connections (Postgres)")
    args = parser.parse_args()

    db_url_env = os.environ.get("DATABASE_URL")
    if not db_url_env:
        print("ERROR: DATABASE_URL must be set.", file=sys.stderr)
        sys.exit(2)

    url = make_url(db_url_env)
    backend = url.get_backend_name()
    ensure_sync_driver(url.drivername)

    target_db = url.database
    if not target_db and not backend.startswith("sqlite"):
        print("ERROR: DATABASE_URL must include a database name.", file=sys.stderr)
        sys.exit(2)

    # ADMIN engine: maintenance DB, AUTOCOMMIT, no transaction
    # admin_url = build_admin_url(url, backend)
    admin_url = url.set(database="postgres")
    admin_engine: Engine = create_engine(
        admin_url,
        future=True,
        pool_pre_ping=True,
        echo=args.echo,
        isolation_level="AUTOCOMMIT",
    )

    try:
        admin_sql = read_sql_file(args.admin_sql)
        run_admin_sql(admin_engine, admin_sql, backend, target_db, args.force)
        print("Admin SQL executed successfully.")
    except SQLAlchemyError as e:
        print(f"ERROR executing admin SQL: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        admin_engine.dispose()

    # APP engine: target DB, transactional
    app_engine: Engine = create_engine(
        url.set(database="cmrt_dev"),
        future=True,
        pool_pre_ping=True,
        echo=args.echo,
    )

    try:
        schema_sql = read_sql_file(args.schema_sql)
        run_schema_sql(app_engine, schema_sql, backend, args.timeout)
        print("Schema SQL executed successfully.")
    except SQLAlchemyError as e:
        print(f"ERROR executing schema SQL: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        app_engine.dispose()


if __name__ == "__main__":
    main()