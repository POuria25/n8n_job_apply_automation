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

The original Compose file reads these three variables:

```dotenv
PG_PASSWORD=REPLACE_WITH_A_STRONG_DATABASE_PASSWORD
N8N_ENCRYPTION_KEY=REPLACE_WITH_A_PRIVATE_RANDOM_ENCRYPTION_KEY
TELEGRAM_TOKEN=REPLACE_WITH_YOUR_BOT_TOKEN
```

Do not overwrite an existing working `.env`. Keep an existing n8n encryption key when restoring its credential database; replacing it arbitrarily can prevent decryption.

The earlier sanitized distribution additionally uses `SENDER_EMAIL`. If adopting that variant, add this to `.env.example` and your local `.env`:

```dotenv
SENDER_EMAIL=applicant@example.com
```

Pass it under the n8n service's `environment` list:

```yaml
- SENDER_EMAIL=${SENDER_EMAIL}
```

Then use this expression in **WF4 → Send email → From Email**:

```text
={{ $json.sender_name }} <{{ $env.SENDER_EMAIL }}>
```

For the uploaded workflow with `<YOUR EMAIL>`, replacing that placeholder privately is also valid. A From address is personal configuration, not a password. It must be authorized by the selected SMTP account. One environment variable still means one sender account; it does not implement separate mailboxes for multiple applicants.

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

The Dockerfile installs Tectonic through an external installer and uses `n8nio/n8n:latest`. The reviewed files do not establish a tested n8n version. Record and pin a compatible version after testing; a floating image is not a reproducible release. The memory limits are settings from the supplied deployment, not verified minimum requirements.

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

**The original application schema was not supplied.** Compose creates the n8n metadata database; it does not create the application's tables. Do not treat the inferred schema in older drafts as a verified migration.

The workflows require these fields:

| Table | Referenced fields |
|---|---|
| `bot_state` | `key`, `value`; a row with key `tg_offset` |
| `applicants` | `id`, `chat_id`, `sender_name`, `phone`, `skeleton_file`, `email_sample_file`, `cv_file`, `daily_limit` |
| `targets` | `id`, `applicant_id`, `company`, `email`, `email_domain`, `address`, `postcity`, `contact`, `hr_email`, `status`, `mx_ok`, `subject`, `email_body`, `letter_pdf`, `error`, `attempts`, `approved_at`, `sent_at` |
| `conversations` | `chat_id`, `step`, `data`, `updated_at` |

Obtain a reviewed schema-only migration from the working installation, or implement and test one against all queries. Required behavior includes generated target IDs, new targets starting at `new`, initialized attempt counts, JSON dialog data, and a unique `conversations.chat_id` for the upsert.

Choose duplicate rules deliberately. A unique employer domain per applicant would also block two unrelated employers using the same public email provider. The bot's duplicate message is not evidence of the actual database constraints.

Keep application data in a separate database such as `candidature` if that matches your installation. All workflow Postgres nodes must use that database; n8n's metadata database remains `n8n`. Database names and schema must agree with your actual provisioning.

After the schema exists, register an applicant with their private chat ID, sender name, document paths, and daily limit. Initialize `bot_state.tg_offset` for a fresh bot. Do not reset an existing offset without understanding which updates would be replayed.

Verify the database session timezone with `SHOW TIMEZONE;`. WF4 uses `sent_at::date = current_date` for the cap, while the schedule follows n8n's timezone.

## 4. Add private documents

| Container path | Expected content |
|---|---|
| `/data/assets/letter_skeleton.tex` | Cover-letter template, referenced by the applicant record |
| `/data/assets/email_sample.txt` | Email body sample, referenced by the applicant record |
| `/data/assets/cv.pdf` | CV, referenced by the applicant record |
| `/data/assets/declaration.pdf` | Declaration, currently hardcoded in WF4 |

The filenames for the first three may differ if the database paths match. Files must be readable by the container's `node` user. `/data/jobs` and the cache must be writable. No private document belongs in the public repository.

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
3. Configure the From address and customize WF3's subject. Confirm all three attachment paths.
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
