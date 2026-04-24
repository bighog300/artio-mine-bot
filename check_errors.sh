#!/bin/bash

set -u

echo "=== CHECKING SMART MINE ERROR ==="
docker compose logs api --tail=300 | grep -A20 "smart-mine.*500" | tail -30

echo ""
echo "=== CHECKING DELETE SOURCE ERROR ==="
docker compose logs api --tail=300 | grep -A20 "DELETE.*sources.*500" | tail -30

echo ""
echo "=== CHECKING FOR INTEGRITY ERRORS ==="
docker compose logs api --tail=300 | grep -A10 "IntegrityError"

echo ""
echo "=== CHECKING FOR FOREIGN KEY ERRORS ==="
docker compose logs api --tail=300 | grep -A10 "ForeignKeyViolation"
