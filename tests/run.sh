#!/usr/bin/env bash
# Starts a throwaway PostgreSQL 16 server in Docker, runs the tests, removes the server.
# To use a server you already have, skip this script: set PGHOST, PGPORT, PGUSER and
# PGPASSWORD for a role that may create databases, then run  python3 tests/test_workflows.py
set -euo pipefail
cd "$(dirname "$0")/.."
name="candidature-tests-$$"
export PGHOST=127.0.0.1 PGPORT="${PGPORT:-55432}" PGUSER=postgres PGPASSWORD=tests PGDATABASE=postgres
docker run -d --rm --name "$name" -e POSTGRES_PASSWORD="$PGPASSWORD" -p "127.0.0.1:${PGPORT}:5432" postgres:16-alpine >/dev/null
trap 'docker stop "$name" >/dev/null' EXIT
for _ in $(seq 1 60); do
  if psql -c 'SELECT 1' >/dev/null 2>&1; then break; fi
  sleep 1
done
python3 tests/test_workflows.py
