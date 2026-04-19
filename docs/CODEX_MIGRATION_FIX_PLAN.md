# 🔧 CODEX EXECUTION PLAN: Migration Fix & Hardening

**Project:** Artio Mine Bot  
**Objective:** Fix broken migration + prevent future migration issues  
**Complexity:** Medium (involves code changes, testing, CI/CD)  
**Estimated Time:** 45-60 minutes for Codex  

---

## 🎯 MISSION STATEMENT

Fix the critical migration bug that prevents fresh deployments, then implement comprehensive safeguards to ensure migrations never break production deployments again.

---

## 📋 EXECUTION PHASES

### **PHASE 1: Fix the Broken Migration** ⏱️ 5 minutes

**Objective:** Correct the boolean default values in migration b2f7e91c4d11

**Files to Modify:**
- `app/db/migrations/versions/b2f7e91c4d11_add_backfill_schedule_policy_tables.py`

**Changes Required:**

```python
# Line 30 - CHANGE:
sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
# TO:
sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),

# Line 31 - CHANGE:
sa.Column("auto_start", sa.Boolean(), nullable=False, server_default=sa.text("0")),
# TO:
sa.Column("auto_start", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),

# Line 51 - CHANGE:
sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
# TO:
sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
```

**Verification:**
```bash
# Search for any remaining boolean bugs
grep -r 'server_default=sa.text("[01]")' app/db/migrations/
# Should return: no matches

# Verify the fixes are in place
grep -r 'server_default=sa.text("TRUE")' app/db/migrations/versions/b2f7e91c4d11_*
# Should return: 2 matches

grep -r 'server_default=sa.text("FALSE")' app/db/migrations/versions/b2f7e91c4d11_*
# Should return: 1 match
```

---

### **PHASE 2: Create Migration Test Suite** ⏱️ 15 minutes

**Objective:** Add automated tests to catch migration bugs before they reach production

**New File:** `tests/test_migrations.py`

```python
"""
Migration Testing Suite

Tests to ensure migrations can run successfully on clean databases
and follow best practices.
"""
import asyncio
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import command
from alembic.config import Config
from app.db.database import Base


@pytest.mark.asyncio
async def test_migrations_from_scratch(test_database_url):
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


@pytest.mark.asyncio
async def test_migrations_up_and_down(test_database_url):
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
        
        if not has_downgrade:
            missing_downgrade.append(filepath)
    
    if missing_downgrade:
        error_msg = "Migrations without proper downgrade implementations:\n"
        for filepath in missing_downgrade:
            error_msg += f"  {filepath}\n"
        pytest.fail(error_msg)


@pytest.mark.asyncio
async def test_critical_tables_exist_after_migration(test_database_url):
    """
    Verify that critical tables are created by migrations.
    """
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_database_url.replace("+asyncpg", ""))
    
    # Run migrations
    command.upgrade(alembic_cfg, "head")
    
    # Check for critical tables
    engine = create_async_engine(test_database_url)
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        tables = {row[0] for row in result}
    
    await engine.dispose()
    
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
```

**New File:** `tests/conftest.py` (if it doesn't exist, or add to existing)

```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
import os


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_database_url():
    """
    Provide a clean test database URL for migration testing.
    
    Creates a new database for each test, runs the test, then drops it.
    """
    # Use a test database
    base_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/artio")
    test_db_name = f"artio_test_{os.getpid()}_{id(asyncio.current_task())}"
    
    # Connection to postgres database to create test db
    admin_url = base_url.rsplit('/', 1)[0] + '/postgres'
    admin_engine = create_async_engine(admin_url.replace('+asyncpg', ''), isolation_level="AUTOCOMMIT")
    
    async with admin_engine.begin() as conn:
        await conn.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
        await conn.execute(f"CREATE DATABASE {test_db_name}")
    
    await admin_engine.dispose()
    
    # Return test database URL
    test_url = base_url.rsplit('/', 1)[0] + f'/{test_db_name}'
    
    yield test_url
    
    # Cleanup
    admin_engine = create_async_engine(admin_url.replace('+asyncpg', ''), isolation_level="AUTOCOMMIT")
    async with admin_engine.begin() as conn:
        await conn.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
    await admin_engine.dispose()
```

---

### **PHASE 3: Add Pre-commit Migration Linter** ⏱️ 10 minutes

**Objective:** Catch migration issues before they're committed

**New File:** `scripts/check_migrations.py`

```python
#!/usr/bin/env python3
"""
Migration Linter

Checks migration files for common issues before they're committed.
Run as part of pre-commit hooks or CI pipeline.
"""
import sys
import glob
import re
from typing import List, Dict


class MigrationChecker:
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def check_boolean_defaults(self, filepath: str, content: str):
        """Check for boolean columns with integer defaults."""
        pattern = re.compile(r'sa\.Boolean\([^)]*server_default=sa\.text\(["\']([01])["\']\)')
        matches = list(pattern.finditer(content))
        
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            self.errors.append(
                f"{filepath}:{line_num} - Boolean column has integer default '{match.group(1)}'. "
                f"Use 'TRUE' or 'FALSE' instead."
            )
    
    def check_downgrade_exists(self, filepath: str, content: str):
        """Check that downgrade function is implemented."""
        if 'def downgrade()' not in content:
            self.errors.append(f"{filepath} - Missing downgrade() function")
            return
        
        # Check it's not just 'pass'
        if re.search(r'def downgrade\([^)]*\):\s*pass\s*$', content, re.MULTILINE):
            self.warnings.append(f"{filepath} - downgrade() only contains 'pass'")
    
    def check_sql_injection_risks(self, filepath: str, content: str):
        """Check for potential SQL injection vulnerabilities."""
        dangerous_patterns = [
            (r'\.execute\(["\'].*%s', 'String formatting in SQL'),
            (r'\.execute\(["\'].*\{', 'f-string or .format() in SQL'),
            (r'\.execute\([f"\']', 'f-string in execute()'),
        ]
        
        for pattern, description in dangerous_patterns:
            if re.search(pattern, content):
                line_num = content[:re.search(pattern, content).start()].count('\n') + 1
                self.warnings.append(
                    f"{filepath}:{line_num} - {description}. Use parameterized queries."
                )
    
    def check_foreign_key_constraints(self, filepath: str, content: str):
        """Check that foreign keys are properly defined."""
        # Look for ForeignKeyConstraint without on_delete
        pattern = re.compile(r'sa\.ForeignKeyConstraint\([^)]*\)')
        matches = list(pattern.finditer(content))
        
        for match in matches:
            if 'ondelete=' not in match.group(0):
                line_num = content[:match.start()].count('\n') + 1
                self.warnings.append(
                    f"{filepath}:{line_num} - ForeignKey without ondelete. "
                    f"Consider CASCADE, SET NULL, or RESTRICT."
                )
    
    def check_index_naming(self, filepath: str, content: str):
        """Check that indexes follow naming conventions."""
        pattern = re.compile(r'create_index\(["\']([^"\']+)["\']')
        matches = list(pattern.finditer(content))
        
        for match in matches:
            index_name = match.group(1)
            if not index_name.startswith('ix_'):
                line_num = content[:match.start()].count('\n') + 1
                self.warnings.append(
                    f"{filepath}:{line_num} - Index '{index_name}' doesn't follow "
                    f"naming convention 'ix_tablename_columnname'"
                )
    
    def check_all_migrations(self) -> bool:
        """Run all checks on all migration files."""
        migration_files = glob.glob("app/db/migrations/versions/*.py")
        
        if not migration_files:
            self.errors.append("No migration files found!")
            return False
        
        for filepath in migration_files:
            with open(filepath, 'r') as f:
                content = f.read()
            
            self.check_boolean_defaults(filepath, content)
            self.check_downgrade_exists(filepath, content)
            self.check_sql_injection_risks(filepath, content)
            self.check_foreign_key_constraints(filepath, content)
            self.check_index_naming(filepath, content)
        
        return len(self.errors) == 0
    
    def print_results(self):
        """Print all errors and warnings."""
        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"  {error}")
            print()
        
        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
            print()
        
        if not self.errors and not self.warnings:
            print("✅ All migration checks passed!")


def main():
    checker = MigrationChecker()
    success = checker.check_all_migrations()
    checker.print_results()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
```

**Make it executable:**
```bash
chmod +x scripts/check_migrations.py
```

---

### **PHASE 4: Add GitHub Actions CI/CD** ⏱️ 15 minutes

**Objective:** Automatically test migrations on every push/PR

**New File:** `.github/workflows/test-migrations.yml`

```yaml
name: Test Database Migrations

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test-migrations:
    name: Test Migrations from Scratch
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: artio_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio
      
      - name: Run migration linter
        run: |
          python scripts/check_migrations.py
      
      - name: Test migrations from scratch
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/artio_test
        run: |
          pytest tests/test_migrations.py::test_migrations_from_scratch -v
      
      - name: Test migration up/down
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/artio_test
        run: |
          pytest tests/test_migrations.py::test_migrations_up_and_down -v
      
      - name: Run all migration tests
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/artio_test
        run: |
          pytest tests/test_migrations.py -v

  lint-migrations:
    name: Lint Migration Files
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Check for boolean integer defaults
        run: |
          if grep -r 'server_default=sa.text("[01]")' app/db/migrations/versions/; then
            echo "❌ Found boolean columns with integer defaults!"
            echo "Use 'TRUE' or 'FALSE' instead of '1' or '0'"
            exit 1
          else
            echo "✅ No boolean integer defaults found"
          fi
      
      - name: Check all migrations have downgrade
        run: |
          python scripts/check_migrations.py
```

---

### **PHASE 5: Add Migration Documentation** ⏱️ 10 minutes

**Objective:** Document best practices for writing migrations

**New File:** `docs/MIGRATION_GUIDE.md`

```markdown
# Migration Best Practices Guide

## ✅ DO's

### Boolean Defaults
```python
# ✅ CORRECT
sa.Column("enabled", sa.Boolean(), server_default=sa.text("TRUE"))
sa.Column("is_active", sa.Boolean(), server_default=sa.text("FALSE"))

# ❌ WRONG - PostgreSQL doesn't accept integer defaults for booleans
sa.Column("enabled", sa.Boolean(), server_default=sa.text("1"))
sa.Column("is_active", sa.Boolean(), server_default=sa.text("0"))
```

### Foreign Keys
```python
# ✅ CORRECT - Specify ondelete behavior
sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE")

# ⚠️ WARNING - No ondelete specified, defaults to NO ACTION
sa.ForeignKeyConstraint(["user_id"], ["users.id"])
```

### Index Naming
```python
# ✅ CORRECT - Follow naming convention
op.create_index("ix_users_email", "users", ["email"])

# ❌ WRONG - Unclear naming
op.create_index("user_email_idx", "users", ["email"])
```

### Downgrade Implementations
```python
# ✅ CORRECT - Proper downgrade
def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

# ❌ WRONG - Just pass, no actual rollback
def downgrade() -> None:
    pass
```

### Parameterized Queries
```python
# ✅ CORRECT - Use sa.text() with parameters
op.execute(sa.text("UPDATE users SET role = :role WHERE id = :id").bindparams(role="admin", id=1))

# ❌ WRONG - String formatting (SQL injection risk)
op.execute(f"UPDATE users SET role = '{role}' WHERE id = {user_id}")
```

## 📋 Migration Checklist

Before committing a migration, verify:

- [ ] Boolean columns use TRUE/FALSE, not 1/0
- [ ] Foreign keys specify ondelete behavior
- [ ] Indexes follow naming convention (ix_tablename_columnname)
- [ ] downgrade() is properly implemented
- [ ] No SQL injection vulnerabilities (no string formatting in SQL)
- [ ] Migration tested locally with `alembic upgrade head`
- [ ] Migration tested with up/down: `alembic downgrade -1 && alembic upgrade +1`

## 🧪 Testing Migrations Locally

```bash
# Test from scratch
docker-compose down -v
docker-compose up -d
sleep 15
docker-compose exec api alembic upgrade head

# Test up and down
docker-compose exec api alembic downgrade -1
docker-compose exec api alembic upgrade +1

# Run migration linter
python scripts/check_migrations.py

# Run migration tests
pytest tests/test_migrations.py -v
```

## 🚨 Common Mistakes

### 1. Boolean Integer Defaults
**Problem:** PostgreSQL doesn't accept integer defaults for boolean columns

**Fix:**
```python
# Change from:
server_default=sa.text("1")
# To:
server_default=sa.text("TRUE")
```

### 2. Missing Downgrade
**Problem:** Cannot rollback if deployment fails

**Fix:** Always implement proper downgrade logic

### 3. SQL Injection
**Problem:** String formatting in SQL queries

**Fix:** Use parameterized queries with sa.text().bindparams()

## 📚 Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Core](https://docs.sqlalchemy.org/en/20/core/)
- [PostgreSQL Data Types](https://www.postgresql.org/docs/current/datatype-boolean.html)
```

**Update:** `README.md`

Add section:

```markdown
## 🗄️ Database Migrations

This project uses Alembic for database migrations.

### Running Migrations

```bash
# Fresh deployment
docker-compose up -d
docker-compose exec api alembic upgrade head

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Rollback one migration
docker-compose exec api alembic downgrade -1
```

### Testing Migrations

Before pushing migration changes:

```bash
# Run migration linter
python scripts/check_migrations.py

# Run migration tests
pytest tests/test_migrations.py -v

# Test from scratch
docker-compose down -v
docker-compose up -d
docker-compose exec api alembic upgrade head
```

See [Migration Guide](docs/MIGRATION_GUIDE.md) for best practices.
```

---

### **PHASE 6: Add Pre-commit Hook** ⏱️ 5 minutes

**Objective:** Prevent committing broken migrations

**New File:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: check-migrations
        name: Check Migration Files
        entry: python scripts/check_migrations.py
        language: system
        files: ^app/db/migrations/versions/.*\.py$
        pass_filenames: false
      
      - id: no-boolean-integers
        name: No Boolean Integer Defaults
        entry: bash -c 'if grep -r "server_default=sa.text(\"[01]\")" app/db/migrations/versions/; then echo "❌ Boolean columns must use TRUE/FALSE, not 1/0"; exit 1; fi'
        language: system
        files: ^app/db/migrations/versions/.*\.py$
        pass_filenames: false
```

**Installation Instructions** (add to README.md):

```markdown
### Setting Up Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```
```

---

### **PHASE 7: Create Fresh Deployment Verification Script** ⏱️ 5 minutes

**Objective:** One-command verification that fresh deployment works

**New File:** `scripts/verify_fresh_deployment.sh`

```bash
#!/bin/bash
set -e

echo "🧪 Testing Fresh Deployment from Scratch"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup
echo "📦 Cleaning up existing deployment..."
docker-compose down -v >/dev/null 2>&1
docker volume rm artio-mine-bot_postgres_data >/dev/null 2>&1 || true
echo "✅ Cleanup complete"
echo ""

# Start services
echo "🚀 Starting services..."
docker-compose up -d
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to start services${NC}"
    exit 1
fi
echo "✅ Services started"
echo ""

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 20
echo "✅ PostgreSQL should be ready"
echo ""

# Run migrations
echo "🗄️  Running database migrations..."
docker-compose exec -T api alembic upgrade head
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Migrations failed!${NC}"
    echo ""
    echo "Logs:"
    docker-compose logs api | tail -50
    exit 1
fi
echo "✅ Migrations completed successfully"
echo ""

# Check migration status
echo "📊 Checking migration status..."
MIGRATION_STATUS=$(docker-compose exec -T api alembic current 2>&1)
echo "$MIGRATION_STATUS"
echo ""

# Test API
echo "🔌 Testing API endpoints..."

# Test sources endpoint
SOURCES_RESPONSE=$(curl -s http://localhost:8765/api/sources)
if echo "$SOURCES_RESPONSE" | grep -q "items"; then
    echo -e "${GREEN}✅ /api/sources responding correctly${NC}"
else
    echo -e "${RED}❌ /api/sources not responding correctly${NC}"
    echo "Response: $SOURCES_RESPONSE"
    exit 1
fi

# Test health endpoint
HEALTH_RESPONSE=$(curl -s http://localhost:8765/api/health || echo "failed")
if echo "$HEALTH_RESPONSE" | grep -q "status"; then
    echo -e "${GREEN}✅ /api/health responding correctly${NC}"
else
    echo -e "${YELLOW}⚠️  /api/health not responding (may not exist)${NC}"
fi
echo ""

# Test frontend
echo "🎨 Testing frontend..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173)
if [ "$FRONTEND_STATUS" == "200" ]; then
    echo -e "${GREEN}✅ Frontend accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend returned status: $FRONTEND_STATUS${NC}"
fi
echo ""

# Check tables exist
echo "🗃️  Verifying database tables..."
TABLES=$(docker-compose exec -T db psql -U postgres -d artio -t -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';" 2>/dev/null | tr -d ' ')
if [ "$TABLES" -gt 15 ]; then
    echo -e "${GREEN}✅ Database has $TABLES tables${NC}"
else
    echo -e "${RED}❌ Expected 15+ tables, found $TABLES${NC}"
    exit 1
fi
echo ""

# Final status
echo "========================================"
echo -e "${GREEN}🎉 Fresh Deployment Successful!${NC}"
echo ""
echo "📍 Access Points:"
echo "   Frontend: http://localhost:5173"
echo "   API: http://localhost:8765"
echo "   API Docs: http://localhost:8765/docs"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "✅ All checks passed. Application ready to use!"
```

**Make it executable:**
```bash
chmod +x scripts/verify_fresh_deployment.sh
```

---

## 🎯 EXECUTION CHECKLIST

Execute phases in order. Each phase must pass before proceeding.

- [ ] **Phase 1:** Fix migration file (3 character changes)
  - [ ] Modify b2f7e91c4d11 lines 30, 31, 51
  - [ ] Verify no more boolean integer defaults exist
  - [ ] Commit: "fix: correct boolean defaults in backfill migration"

- [ ] **Phase 2:** Create migration test suite
  - [ ] Create tests/test_migrations.py
  - [ ] Update tests/conftest.py
  - [ ] Run tests locally: `pytest tests/test_migrations.py -v`
  - [ ] Commit: "test: add comprehensive migration test suite"

- [ ] **Phase 3:** Add migration linter
  - [ ] Create scripts/check_migrations.py
  - [ ] Make executable: `chmod +x scripts/check_migrations.py`
  - [ ] Run locally: `python scripts/check_migrations.py`
  - [ ] Commit: "chore: add migration linter script"

- [ ] **Phase 4:** Add GitHub Actions CI
  - [ ] Create .github/workflows/test-migrations.yml
  - [ ] Push and verify workflow runs
  - [ ] Commit: "ci: add migration testing to GitHub Actions"

- [ ] **Phase 5:** Add documentation
  - [ ] Create docs/MIGRATION_GUIDE.md
  - [ ] Update README.md with migration section
  - [ ] Commit: "docs: add migration best practices guide"

- [ ] **Phase 6:** Add pre-commit hook
  - [ ] Create .pre-commit-config.yaml
  - [ ] Update README.md with setup instructions
  - [ ] Commit: "chore: add pre-commit hooks for migrations"

- [ ] **Phase 7:** Create verification script
  - [ ] Create scripts/verify_fresh_deployment.sh
  - [ ] Make executable: `chmod +x scripts/verify_fresh_deployment.sh`
  - [ ] Run locally: `./scripts/verify_fresh_deployment.sh`
  - [ ] Commit: "test: add fresh deployment verification script"

---

## ✅ FINAL VERIFICATION

After all phases complete, run this comprehensive check:

```bash
# 1. Lint migrations
python scripts/check_migrations.py

# 2. Run migration tests
pytest tests/test_migrations.py -v

# 3. Verify fresh deployment
./scripts/verify_fresh_deployment.sh

# 4. Check GitHub Actions
# Push to repo and verify CI passes
```

**Success Criteria:**
- ✅ All migration linter checks pass
- ✅ All pytest migration tests pass
- ✅ Fresh deployment script completes successfully
- ✅ GitHub Actions workflow passes
- ✅ API returns JSON on fresh deployment
- ✅ Frontend loads without errors

---

## 📦 DELIVERABLES

**Code Changes:**
1. Fixed migration file (b2f7e91c4d11)
2. Migration test suite (tests/test_migrations.py)
3. Migration linter (scripts/check_migrations.py)
4. GitHub Actions workflow (.github/workflows/test-migrations.yml)
5. Migration guide (docs/MIGRATION_GUIDE.md)
6. Pre-commit config (.pre-commit-config.yaml)
7. Verification script (scripts/verify_fresh_deployment.sh)
8. Updated README.md

**Total Files Modified:** 1  
**Total Files Created:** 7  
**Total Lines Added:** ~1,000  

**Testing Coverage:**
- Fresh deployment from scratch
- Migration up/down cycles
- Boolean default validation
- SQL injection pattern detection
- Downgrade implementation checks
- Foreign key constraint validation
- Index naming convention checks

---

## 🚀 POST-DEPLOYMENT

After merge to main:

1. **Tag Release:**
   ```bash
   git tag -a v1.0.0-migration-fix -m "Fix: Critical migration bug + hardening"
   git push origin v1.0.0-migration-fix
   ```

2. **Update Documentation:**
   - Add to CHANGELOG.md
   - Update deployment docs
   - Notify team of changes

3. **Monitor:**
   - Watch GitHub Actions for any failures
   - Monitor deployment success rate
   - Collect developer feedback

---

## 💡 FUTURE IMPROVEMENTS

**Phase 8 (Optional):**
- Add migration performance tests (large dataset migrations)
- Add migration idempotency tests
- Add database schema diff validation
- Add automated migration generation checks

**Phase 9 (Optional):**
- Database backup/restore before migrations
- Blue/green deployment support
- Zero-downtime migration strategies
- Migration rollback automation

---

**End of Execution Plan**

**Estimated Total Time:** 45-60 minutes  
**Risk Level:** Low (mostly additions, one critical fix)  
**Breaking Changes:** None  
**Database Impact:** Fixes existing deployment blocker  

**Ready for Codex execution! 🚀**
