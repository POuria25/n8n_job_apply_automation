# Testing

[Back to README](../README.md)

`tests/test_workflows.py` reads the SQL out of `workflows/*.json` and runs it against `db/schema.sql` on a real PostgreSQL server. Because the queries are taken from the workflow files, a change to a workflow query is tested without copying it anywhere.

## What is covered

| Area | Checks |
|---|---|
| Schema | Applies cleanly, applies twice, keeps the Telegram offset, upgrades an older table in place |
| Every workflow query | All 18 run, with values passed both as literals and as bound parameters |
| Entry | Dialog session round-trip, inserts, duplicate rules, empty optional fields |
| Approval buttons | Stale button after Refaire, button from before a redraft, repeated approval, unknown action, other applicant |
| Drafting | Version incremented per draft, draft saved before preview, failed preview retried and capped |
| Sending | Daily limit, in-flight sends counted, late or repeated result reports ignored |
| Concurrency | 12 simultaneous sending runs claim one application once; an overlapping run cannot claim for the same applicant; repeated overlapping runs stay within the daily limit; same for drafting and MX claims |
| Stale claims | `checking` and `drafting` taken back after 15 minutes; `sending` never taken back |
| Button parser | The `Parse callback` code from WF1 on valid and malformed button data (needs `node`) |

## What is not covered

Anything that needs n8n, Telegram, or a mail server: node wiring, expressions, credentials, the LaTeX build inside the container, the guided dialog end to end, and actual delivery. After changing a workflow, import it into a test instance and send one application to an address you control.

## Running

With Docker and the PostgreSQL client tools installed:

```bash
tests/run.sh
```

The script starts a throwaway `postgres:16-alpine` container, runs the tests, and removes it. To use a server you already have, set `PGHOST`, `PGPORT`, `PGUSER`, and `PGPASSWORD` for a role that may create databases, then run:

```bash
python3 tests/test_workflows.py
```

The tests create and drop databases named `wf_test_*`. They never touch other databases, but do not point them at a server where such names are in use.

The same tests run on GitHub for every push and pull request (`.github/workflows/tests.yml`).
