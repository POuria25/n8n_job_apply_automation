# The workflows in n8n

[Back to README](../README.md)

Screenshots of the four workflows in the n8n editor, and where each file in the repository fits. Node-by-node behaviour and known limitations are in [Operations and limitations](OPERATIONS.md).

## WF1 — Telegram poller

Runs every 5 seconds. Polls Telegram, checks the chat against the allowlist, then routes each update: bulk lines, approval buttons, uploaded text files, commands, or the guided dialog.

![WF1 Telegram poller workflow in the n8n editor](images/wf1-telegram-poller.png)

## WF2 — MX check

Runs every 2 minutes. Claims up to 10 new employers, looks up the MX records of each email domain, and warns the applicant when a domain does not accept mail.

![WF2 MX check workflow in the n8n editor](images/wf2-mx-check.png)

## WF3 — Drafting

Runs every 3 minutes. Fills the LaTeX template for one employer and compiles it. The upper branch sends the PDF preview with its approval buttons; the lower one reports a compilation error.

![WF3 Drafting workflow in the n8n editor](images/wf3-drafting.png)

## WF4 — Sending

Runs on weekdays, every 30 minutes from 08:00 to 17:30. Takes one approved application per applicant, attaches the letter, CV, and declaration, and sends it. The lower branch records an SMTP error.

![WF4 Sending workflow in the n8n editor](images/wf4-sending.png)

## Repository layout

| Path | Purpose |
|---|---|
| `workflows/WF1-Telegram-poller.json` | Telegram interface |
| `workflows/WF2-MX-check.json` | Domain checks |
| `workflows/WF3-Drafting.json` | PDF generation |
| `workflows/WF4-Sending.json` | Email sending |
| `Dockerfile` | n8n 2.42.4 image with Tectonic |
| `docker-compose.yml` | Containers, environment, and volumes |
| `db/schema.sql` | Application tables, constraints, and initial state |
| `db/applicant.example.sql` | Fictional applicant record to copy and fill in |
| `examples/` | Fictional letter and email templates to copy into `assets/` |
| `tests/` | Database tests for the workflow queries |
| `.env.example` | Configuration names with placeholders only |
| `docs/` | Setup, operations, publishing, demo, and this page |

Private `assets/` and runtime volumes are intentionally excluded from the repository.
