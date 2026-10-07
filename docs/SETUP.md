# Installation and credentials

[Back to README](../README.md)

This guide follows the supplied Compose configuration. It does not replace it with an unrelated example. Commands assume Bash on the Docker host and standard filenames `Dockerfile` and `docker-compose.yml`.

## 1. Prepare the configuration

For a **new installation**, copy the public example and fill it locally:

```bash
cp .env.example .env
chmod 600 .env
mkdir -p assets
```

Compose reads these four variables:

```dotenv
PG_PASSWORD=REPLACE_WITH_A_STRONG_DATABASE_PASSWORD
N8N_ENCRYPTION_KEY=REPLACE_WITH_A_PRIVATE_RANDOM_ENCRYPTION_KEY
TELEGRAM_TOKEN=REPLACE_WITH_YOUR_TELEGRAM_BOT_TOKEN
SENDER_EMAIL=applicant@example.com
```

Do not overwrite an existing working `.env`. Keep an existing n8n encryption key when restoring its credential database; replacing it arbitrarily can prevent decryption.

`SENDER_EMAIL` is the From address of every application. Compose passes it to n8n, and **WF4 → Send email → From Email** reads it:

```text
={{ $json.sender_name }} <{{ $env.SENDER_EMAIL }}>
```

A From address is personal configuration, not a password, but it must be authorized by the SMTP account selected in n8n. One variable means one sender account: it does not give several applicants separate mailboxes. If the variable is missing, the From field is empty and sending fails, so recreate the n8n container after editing `.env` (`docker compose up -d`).

## 2. Understand the supplied deployment

| Setting | Supplied configuration |
|---|---|
| PostgreSQL service | `postgres`, image `postgres:16-alpine` |
| n8n metadata database | `n8n` |
| PostgreSQL user | `n8n` |
| n8n listener | Host loopback `127.0.0.1:5678` |
| Private asset mount | Host `./assets` → container `/data/assets`, read-only |
| Generated letters | Named volume `jobs` → `/data/jobs` |
| Tectonic cache | Named volume `tectonic_cache` → `/data/tectonic-cache` |
| n8n local data | Named volume `n8n_data` → `/home/node/.n8n` |
| PostgreSQL data | Named volume `pg_data` → `/var/lib/postgresql/data` |

The Dockerfile pins `n8nio/n8n:2.42.4`, the version the original installation reports from `n8n --version`. The workflows have not been tested on other versions; change the tag deliberately and retest when upgrading. Tectonic is still installed through an external installer that fetches its current release, so that part of the image is not pinned. The memory limits are settings from the supplied deployment, not verified minimum requirements.

Compose enables environment access, allows `/data` for file nodes, and sets `NODES_EXCLUDE=[]` for node availability. WF3 requires Execute Command, `node`, and `tectonic`. Verify these settings against your installed n8n version and restrict editing to trusted operators.

For a fresh deployment with a completed `.env`:

```bash
docker compose up -d --build
docker compose ps
docker compose exec n8n tectonic --version
docker compose exec n8n node --version
```

Open n8n at `http://localhost:5678` on the host. For a remote VPS, an SSH tunnel avoids exposing that listener directly:

```bash
ssh -L 5678:127.0.0.1:5678 USER@YOUR_SERVER
```

Then open `http://localhost:5678` on your computer and complete n8n account setup. The supplied `N8N_SECURE_COOKIE=false` suits this local HTTP configuration; review it when deploying behind HTTPS.

## 3. Provision the application database

Compose creates the n8n metadata database (`n8n`). The application's tables are created separately from [`db/schema.sql`](../db/schema.sql).

That schema was written from the SQL in WF1–WF4 and checked by running all 17 workflow queries against it on PostgreSQL 16. **It is not a dump of the original installation**, so types and constraints may differ from that database. If you are restoring an existing installation, use its own schema.

Create a separate database for the application and load the schema:

```bash
docker compose exec -T postgres createdb -U n8n candidature
docker compose exec -T postgres psql -U n8n -d candidature -v ON_ERROR_STOP=1 < db/schema.sql
```

The script can be run again safely: it creates only what is missing and does not reset the Telegram offset.

| Table | Purpose |
|---|---|
| `bot_state` | Telegram polling offset, in the row with key `tg_offset` (created with value `0`) |
| `applicants` | One row per applicant; `chat_id` is the Telegram allowlist |
| `targets` | One row per employer, with the pipeline `status` |
| `conversations` | Guided-entry dialog state, one row per chat |

Register an applicant. Copy [`db/applicant.example.sql`](../db/applicant.example.sql) to a private file, replace every value (chat ID, sender name, document paths, daily limit), and run it once:

```bash
cp db/applicant.example.sql applicant.local.sql
docker compose exec -T postgres psql -U n8n -d candidature -v ON_ERROR_STOP=1 < applicant.local.sql
```

Do not commit your filled-in copy. The paths are container paths: files in the host's `./assets` appear under `/data/assets`.

Check the result:

```bash
docker compose exec -T postgres psql -U n8n -d candidature \
  -c "SELECT id, chat_id, sender_name, daily_limit FROM applicants;" \
  -c "SELECT * FROM bot_state;"
```

**Duplicate rules.** For each applicant, the schema allows one employer per company name (ignoring case) and one per email domain, which is what the bot's "existe déjà (même nom ou même domaine email)" reply describes. The domain rule also blocks two different employers that share a mail provider such as `gmail.com`. To allow that:

```sql
DROP INDEX targets_applicant_domain_key;
```

All workflow Postgres nodes must point at the `candidature` database (section 5); n8n's own metadata stays in `n8n`. Do not reset an existing `tg_offset` without understanding which updates would be replayed.

Verify the database session timezone with `SHOW TIMEZONE;`. WF4 uses `sent_at::date = current_date` for the cap, while the schedule follows n8n's timezone. The supplied Compose file does not set a timezone for PostgreSQL, so it defaults to UTC.

## 4. Add private documents

| Container path | Expected content |
|---|---|
| `/data/assets/letter_skeleton.tex` | Cover-letter template, referenced by the applicant record |
| `/data/assets/email_sample.txt` | Email body sample, referenced by the applicant record |
| `/data/assets/cv.pdf` | CV, referenced by the applicant record |
| `/data/assets/declaration.pdf` | Declaration, currently hardcoded in WF4 |

Fictional starting points for the first two are in [`examples/`](../examples/). The filenames for the first three may differ if the database paths match. Files must be readable by the container's `node` user. `/data/jobs` and the cache must be writable. No private document belongs in the public repository.

The LaTeX template must contain `<<RECIPIENT>>` and `<<DATE>>`. WF3 replaces the first occurrence of each. A minimal illustrative template is:

```latex
\documentclass[11pt]{letter}
\usepackage[french]{babel}
\signature{Prénom Nom}
\address{Adresse personnelle}
\date{<<DATE>>}
\begin{document}
\begin{letter}{<<RECIPIENT>>}
\opening{Madame, Monsieur,}
Votre texte de candidature, à personnaliser avant utilisation.
\closing{Veuillez agréer, Madame, Monsieur, mes salutations distinguées.}
\end{letter}
\end{document}
```

Validate the resulting layout with your real template. The email sample should contain the body, without the closing signature: WF4 adds a greeting, `Cordialement,` and the sender name. WF3 removes an initial `Madame, Monsieur,` if present.

## 5. Configure credentials

There are **three n8n credential records**. The same Telegram token is entered in two places. The encryption key is an additional deployment secret, not a service login.

| Input | Where to enter it | Used by |
|---|---|---|
| PostgreSQL connection | n8n credential `Postgres account` | Every Postgres node in WF1–WF4 |
| Telegram bot token | n8n credential `Telegram account` | Telegram nodes in WF1–WF4 |
| Same Telegram bot token | Local `.env`: `TELEGRAM_TOKEN` | WF1 HTTP Request nodes |
| SMTP login and app password | n8n credential `SMTP account` | WF4 `Send email` |
| Database server password | Local `.env`: `PG_PASSWORD` | Compose configures PostgreSQL and n8n's metadata connection |
| n8n encryption key | Local `.env`: `N8N_ENCRYPTION_KEY` | Protects stored n8n credentials |

For workflow PostgreSQL credentials on this Docker network, the host is `postgres`, port `5432`, and database is the application database. If using the supplied `n8n` database role, its password corresponds to `PG_PASSWORD`; a separately provisioned application role has its own credentials.

For Yahoo SMTP:

| Field | Value |
|---|---|
| Host | `smtp.mail.yahoo.com` |
| Port | `465` |
| SSL/TLS | Enabled |
| Username | Your full Yahoo email address |
| Password | A Yahoo-generated app password |

The SMTP password is not present in the uploaded `.env` or workflow exports. Enter it privately in n8n. Credential IDs and names in workflow JSON are references, not the password values. Conversely, secrets manually pasted into node parameters can appear in exports.

In this Compose deployment, n8n stores its credential data in PostgreSQL, persisted through `pg_data`; the encryption key is supplied through the environment. Keep both database backups and the key private. Update both Telegram configurations when replacing the bot token.

There is no AI credential to configure for these workflows. Other workflows or credentials on a live instance were not inspected.

## 6. Import and test

1. Import one canonical copy of each workflow. Keep all four inactive while configuring them; verify this in the UI rather than assuming an import behavior.
2. Assign the correct Postgres, Telegram, and SMTP credentials to all applicable nodes. Remove empty or whitespace-only credential references from public templates.
3. Check that `SENDER_EMAIL` is set and customize WF3's subject. Confirm all three attachment paths.
4. Use a dedicated bot with no active webhook and no other poller. Telegram polling and webhooks are mutually exclusive. Obtain the allowed private chat ID before enabling WF1; keep API URLs containing the bot token out of screenshots and shared logs.
5. Enable WF1 and confirm `/start`, `/nouveau`, and `/stats` work for the registered chat.
6. Add one test employer with an email address you control. Enable WF2 and WF3; inspect the generated PDF and caption.
7. Confirm the destination, email body, CV, and declaration. Approve that test application.
8. Run WF4 once with only the test application queued. Verify actual receipt and attachments, then inspect its database status.
9. Check the schedule timezone and daily limit before enabling normal sending. Avoid overlapping manual and scheduled executions.

This checklist is a procedure for the deployer; it has not been run against your live instance as part of the documentation review.

## Official references

- [Yahoo Mail server settings](https://help.yahoo.com/kb/SLN4075.html)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [n8n encryption key configuration source](https://github.com/n8n-io/n8n-docs/blob/main/docs/deploy/host-n8n/configure-n8n/basic-configuration/configuration-examples/set-a-custom-encryption-key.md)
