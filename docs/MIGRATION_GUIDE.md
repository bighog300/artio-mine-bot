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

Install project + dev dependencies first:

```bash
python -m pip install -e ".[dev]"
```

Then run migration checks:

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
