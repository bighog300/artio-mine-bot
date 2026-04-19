#!/usr/bin/env python3
"""
Migration Linter

Checks migration files for common issues before they're committed.
Run as part of pre-commit hooks or CI pipeline.
"""
import sys
import glob
import re


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
