"""
Migration Testing Suite

Tests to ensure migrations can run successfully on clean databases
and follow best practices.
"""
import pytest
from sqlalchemy import create_engine, text
from alembic import command
from alembic.config import Config


def test_migrations_from_scratch(test_database_url):
    """
    Test that all migrations run successfully on an empty database.

    This is the most critical test - it simulates a fresh deployment.
    """
    # Create alembic config
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_database_url.replace("+asyncpg", ""))

    # Run migrations from scratch
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        pytest.fail(f"Migration failed: {e}")

    # Verify we're at head
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext

    script = ScriptDirectory.from_config(alembic_cfg)

    engine = create_engine(test_database_url.replace("+asyncpg", ""))
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current_heads = context.get_current_heads()
        expected_heads = script.get_heads()

        assert set(current_heads) == set(expected_heads), \
            f"Migration heads mismatch. Current: {current_heads}, Expected: {expected_heads}"


def test_migrations_up_and_down(test_database_url):
    """
    Test that migrations can be upgraded and downgraded without errors.
    """
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_database_url.replace("+asyncpg", ""))

    # Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # Downgrade one step
    command.downgrade(alembic_cfg, "-1")

    # Upgrade back to head
    command.upgrade(alembic_cfg, "head")


def test_no_boolean_integer_defaults():
    """
    Scan all migration files for the boolean/integer bug.

    PostgreSQL boolean columns should use TRUE/FALSE, not 1/0.
    """
    import glob
    import re

    migration_files = glob.glob("app/db/migrations/versions/*.py")

    # Pattern to catch: sa.Boolean() with server_default="0" or "1"
    bad_pattern = re.compile(r'sa\.Boolean\([^)]*server_default=sa\.text\(["\']([01])["\']\)')

    violations = []
    for filepath in migration_files:
        with open(filepath, 'r') as f:
            content = f.read()
            matches = bad_pattern.finditer(content)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                violations.append({
                    'file': filepath,
                    'line': line_num,
                    'value': match.group(1)
                })

    if violations:
        error_msg = "Boolean columns with integer defaults found:\n"
        for v in violations:
            error_msg += f"  {v['file']}:{v['line']} - using '{v['value']}' instead of TRUE/FALSE\n"
        pytest.fail(error_msg)


def test_all_migrations_have_downgrade():
    """
    Ensure all migrations have downgrade paths defined.
    """
    import glob
    import ast

    migration_files = glob.glob("app/db/migrations/versions/*.py")

    missing_downgrade = []
    for filepath in migration_files:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())

        has_downgrade = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'downgrade':
                # Check it's not just 'pass'
                if len(node.body) > 1 or not isinstance(node.body[0], ast.Pass):
                    has_downgrade = True
                    break

        if not has_downgrade and "_merge_" not in filepath:
            missing_downgrade.append(filepath)

    if missing_downgrade:
        error_msg = "Migrations without proper downgrade implementations:\n"
        for filepath in missing_downgrade:
            error_msg += f"  {filepath}\n"
        pytest.fail(error_msg)


def test_critical_tables_exist_after_migration(test_database_url):
    """
    Verify that critical tables are created by migrations.
    """
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_database_url.replace("+asyncpg", ""))

    # Run migrations
    command.upgrade(alembic_cfg, "head")

    # Check for critical tables
    engine = create_engine(test_database_url.replace("+asyncpg", ""))
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
        """))
        tables = {row[0] for row in result}

    engine.dispose()

    critical_tables = {
        'tenants',
        'sources',
        'pages',
        'records',
        'jobs',
        'images',
        'backfill_schedules',
        'backfill_policies',
        'api_keys',
        'audit_events',
    }

    missing = critical_tables - tables
    if missing:
        pytest.fail(f"Critical tables missing after migration: {missing}")


def test_no_sql_injection_vulnerabilities():
    """
    Scan migrations for potential SQL injection patterns.
    """
    import glob
    import re

    migration_files = glob.glob("app/db/migrations/versions/*.py")

    # Pattern to catch: string formatting in SQL (potential injection)
    dangerous_patterns = [
        re.compile(r'\.execute\(["\'].*%s'),  # String formatting
        re.compile(r'\.execute\(["\'].*\{'),  # f-string or .format()
        re.compile(r'\.execute\(["\'].*\+'),  # String concatenation
    ]

    violations = []
    for filepath in migration_files:
        with open(filepath, 'r') as f:
            content = f.read()
            for pattern in dangerous_patterns:
                matches = pattern.finditer(content)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append({
                        'file': filepath,
                        'line': line_num,
                        'pattern': pattern.pattern
                    })

    if violations:
        error_msg = "Potential SQL injection vulnerabilities found:\n"
        for v in violations:
            error_msg += f"  {v['file']}:{v['line']}\n"
        pytest.fail(error_msg)
