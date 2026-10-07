# Commands: monitoring and administration

[Back to README](../README.md)

Commands for watching the pipeline and for the few interventions it needs. Run them from the folder that contains `docker-compose.yml`. They assume the application database is called `candidature`, as in the [setup guide](SETUP.md).

**Every result shown on this page is invented.** Real output contains the names and addresses of employers and contacts: do not paste it into an issue, a chat, or a screenshot.

The page has two parts. [Part 1](#part-1-looking-read-only) only reads. [Part 2](#part-2-changing-data) changes data, and each command there says what to check first.

## Before you start

The commands are written for Bash, with `\` continuing a line. In **PowerShell**, put the whole command on one line, or open a session in the database and paste only the SQL:

```bash
docker compose exec postgres psql -U n8n -d candidature
```

Type `\q` to leave the session. Inside it, end each statement with `;`.

The `status` of an employer record is one of: `new`, `checking`, `email_found`, `no_email`, `drafting`, `awaiting_approval`, `queued`, `sending`, `sent`, `skipped`, `error`.

---

## Part 1: Looking (read-only)

Nothing in this part changes anything.

### Sent applications

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "SELECT id, company, email, sent_at
      FROM targets
      WHERE status = 'sent'
      ORDER BY sent_at DESC
      LIMIT 30;"
```

```text
 id |       company        |          email          |            sent_at
----+----------------------+-------------------------+-------------------------------
 12 | Société Exemple S.A. | recrutement@example.com | 2026-01-15 09:30:04.118+00
 11 | Cabinet Exemple      | contact@example.net     | 2026-01-15 09:00:03.902+00
(2 rows)
```

`sent` means the mail server accepted the message, not that the recipient received it.

### Sending queue

Approved applications waiting for a sending slot, in the order they will go out.

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "SELECT id, company, email, approved_at
      FROM targets
      WHERE status = 'queued'
      ORDER BY approved_at;"
```

### Letters waiting for approval

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "SELECT id, company, email
      FROM targets
      WHERE status = 'awaiting_approval'
      ORDER BY id;"
```

These have a preview in Telegram that nobody has answered yet.

### Statistics

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "SELECT status, count(*) AS total
      FROM targets
      GROUP BY status
      ORDER BY status;"
```

```text
      status       | total
-------------------+-------
 awaiting_approval |     2
 queued            |     3
 sent              |    12
 skipped           |     1
(4 rows)
```

The `/stats` command in Telegram shows the same counts for one applicant.

### Errors

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "SELECT id, company, error
      FROM targets
      WHERE status = 'error'
      ORDER BY id DESC;"
```

The `error` text tells you which step failed: it starts with `Compilation LaTeX` for a letter that did not build, reads `Aperçu non envoyé sur Telegram` for a preview that could not be delivered, and is the mail server's message for a failed send.

### Find one application

By company name, or part of it:

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "SELECT id, company, email, hr_email, status, approved_at, sent_at
      FROM targets
      WHERE company ILIKE '%exemple%'
      ORDER BY id;"
```

By identifier, with every field, one per line:

```bash
docker compose exec postgres psql -U n8n -d candidature -x \
  -c "SELECT * FROM targets WHERE id = 42;"
```

By email domain, which is what the duplicate rule compares:

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "SELECT id, company, email, status
      FROM targets
      WHERE email_domain = 'example.com';"
```

### Work in progress

Records a workflow has claimed and not finished, with how long ago.

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "SELECT id, company, status, claimed_at,
             date_trunc('second', now() - claimed_at) AS since
      FROM targets
      WHERE status IN ('checking', 'drafting', 'sending')
      ORDER BY claimed_at;"
```

```text
 id |     company     |  status  |          claimed_at           |  since
----+-----------------+----------+-------------------------------+----------
 14 | Garage Exemple  | drafting | 2026-01-15 10:03:00.412+00    | 00:00:21
(1 row)
```

A few seconds to a minute is normal. `checking` and `drafting` are taken back automatically after 15 minutes. A record that stays in `sending` for more than a few minutes will not move by itself: see [An application stuck in `sending`](#an-application-stuck-in-sending).

### Today's count against the daily limit

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "SELECT a.id, a.sender_name, a.daily_limit,
             count(t.id) FILTER (WHERE t.status = 'sent' AND t.sent_at::date = current_date) AS sent_today,
             count(t.id) FILTER (WHERE t.status = 'sending') AS sending_now,
             count(t.id) FILTER (WHERE t.status = 'queued') AS queued
      FROM applicants a
      LEFT JOIN targets t ON t.applicant_id = a.id
      GROUP BY a.id
      ORDER BY a.id;"
```

```text
 id |   sender_name   | daily_limit | sent_today | sending_now | queued
----+-----------------+-------------+------------+-------------+--------
  1 | Camille Exemple |          10 |          4 |           0 |      3
(1 row)
```

Sending stops for the day when `sent_today + sending_now` reaches `daily_limit`. "Today" is the database's date; check its timezone with `SHOW TIMEZONE;`.

### Telegram dialog state and polling offset

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "SELECT chat_id, step, updated_at FROM conversations;" \
  -c "SELECT * FROM bot_state;"
```

A `step` other than `done` means an entry was started and not finished.

### Containers and logs

```bash
docker compose ps
docker compose logs --tail=100 n8n
docker compose logs --tail=100 postgres
```

Follow the n8n log live with `docker compose logs -f n8n` (Ctrl+C to stop). Logs can contain employer details too.

The build log of one letter, where `42` is the application's identifier:

```bash
docker compose exec n8n cat /data/jobs/42/compile.log
```

Check that the tools WF3 needs are present:

```bash
docker compose exec n8n n8n --version
docker compose exec n8n tectonic --version
```

---

## Part 2: Changing data

Each command below changes one record that you name by its identifier, and prints what it changed. If it prints `UPDATE 0`, nothing matched and nothing was changed: look at the record again with the "Find one application" commands before trying anything else.

Replace `42` with the real identifier every time. Never run these without the `WHERE id = …` line.

### Change the daily limit

Replace `1` with the applicant's identifier and `15` with the new limit.

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "UPDATE applicants SET daily_limit = 15 WHERE id = 1
      RETURNING id, sender_name, daily_limit;"
```

The new limit applies from the next sending slot. A limit of `0` stops sending for that applicant without touching the queue. WF4 offers 20 slots a day, so a limit above 20 has no further effect.

### Recovery after an error

Start by reading the error (see [Errors](#errors)), then use the matching case.

#### The letter did not compile

Read the build log, fix the template in `assets/`, then send the application back to drafting:

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "UPDATE targets SET status = 'email_found', error = NULL
      WHERE id = 42 AND status = 'error'
      RETURNING id, company, status;"
```

A new preview arrives in Telegram within a few minutes. Nothing is sent until it is approved.

#### The preview could not be delivered

The error is `Aperçu non envoyé sur Telegram`. Check that the applicant has not blocked the bot and that the Telegram credential in n8n is valid, then use the same command as above.

#### The email domain was refused (`no_email`)

If the address is right and the refusal was a temporary DNS problem, send it back to drafting:

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "UPDATE targets SET status = 'email_found'
      WHERE id = 42 AND status = 'no_email'
      RETURNING id, company, email, status;"
```

If the address is wrong, correct it first; see [Correct or remove an employer](#correct-or-remove-an-employer).

#### Sending failed with a mail-server error

The record is in `error` and the `error` text is the mail server's reply, for example an authentication failure. The server refused the message, so it was not sent. **Confirm that before requeuing:**

1. The `error` text is a refusal from the mail server, not empty and not a timeout.
2. There is no `📤 Envoyé à …` notice for this employer in the Telegram chat.
3. The message is not in the sender mailbox's Sent folder.

Fix the cause (usually the SMTP credential in n8n). Then put the application back in the queue:

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "UPDATE targets SET status = 'queued', error = NULL
      WHERE id = 42 AND status = 'error' AND sent_at IS NULL
      RETURNING id, company, email, status;"
```

It goes out at the next sending slot without a new approval. If the error was a timeout or you cannot tell whether the message left, treat it as the next case.

#### An application stuck in `sending`

This is the one case where a wrong move sends the same application twice. The workflow stopped after claiming the record, and the email **may or may not have been sent**.

1. Make sure no WF4 execution is still running in n8n.
2. Look in the sender mailbox's Sent folder and, if you can, ask whether a copy arrived. Mail sent through SMTP does not always appear in the Sent folder, so an empty folder is not proof.
3. Decide:

If the email was sent, or you cannot rule it out, record it as sent. No second email goes out:

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "UPDATE targets SET status = 'sent', sent_at = now(), error = NULL
      WHERE id = 42 AND status = 'sending'
      RETURNING id, company, status, sent_at;"
```

Only if you are sure it was **not** sent, put it back in the queue:

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "UPDATE targets SET status = 'queued'
      WHERE id = 42 AND status = 'sending'
      RETURNING id, company, email, status;"
```

When in doubt, choose the first. A missing application can be sent again later; a duplicate cannot be taken back.

#### A record stuck in `checking` or `drafting`

Wait: these are taken back automatically 15 minutes after they were claimed. Records claimed before the `claimed_at` column existed have it empty and are not taken back; release one by hand with:

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "UPDATE targets SET status = 'new'
      WHERE id = 42 AND status = 'checking'
      RETURNING id, company, status;"
```

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "UPDATE targets SET status = 'email_found'
      WHERE id = 42 AND status = 'drafting'
      RETURNING id, company, status;"
```

### Withdraw an application before it is sent

To stop an approved application that is still in the queue:

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "UPDATE targets SET status = 'skipped'
      WHERE id = 42 AND status IN ('queued', 'awaiting_approval')
      RETURNING id, company, status;"
```

### Correct or remove an employer

The bot has no edit command. To correct a record that has **not** been sent, fix the fields and send it back through the MX check and drafting, so a new preview shows the corrected details:

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "UPDATE targets
      SET company = 'Société Exemple S.A.',
          email = 'recrutement@example.com',
          email_domain = 'example.com',
          status = 'new'
      WHERE id = 42 AND status NOT IN ('sending', 'sent')
      RETURNING id, company, email, status;"
```

`email_domain` must be the part of `email` after the `@`. The command fails with a "duplicate key" error if another record of the same applicant already has that company name or that domain.

To remove a record entirely, for example one entered by mistake that blocks the right employer as a duplicate:

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "DELETE FROM targets
      WHERE id = 42 AND status NOT IN ('sending', 'sent')
      RETURNING id, company, email;"
```

Records that were sent are deliberately excluded: they are the history that prevents writing to the same employer twice.

### Reset a Telegram dialog

If the guided entry is stuck, `/annuler` in the chat is the first thing to try. Otherwise, with the chat's identifier in place of `123456789`:

```bash
docker compose exec postgres psql -U n8n -d candidature \
  -c "UPDATE conversations SET step = 'done', data = '{}'::jsonb, updated_at = now()
      WHERE chat_id = 123456789
      RETURNING chat_id, step;"
```

### Stop and restart

| Goal | Command |
|---|---|
| Stop everything, keep all data | `docker compose stop` |
| Start again | `docker compose start` |
| Restart n8n only | `docker compose restart n8n` |
| Apply a change to `.env` or `docker-compose.yml` | `docker compose up -d` |
| Rebuild after changing the `Dockerfile` | `docker compose up -d --build` |
| Remove the containers, keep all data | `docker compose down` |

**Never add `-v` to `docker compose down`.** It deletes the volumes: both databases, the stored n8n credentials, and every generated letter.

To pause sending without stopping the bot, deactivate WF4 in the n8n editor. Entries, checks, and previews continue, and approved applications wait in the queue. Stopping n8n in the middle of a sending slot can leave a record in `sending`; check [Work in progress](#work-in-progress) after a restart.

### Backup

A backup has four parts. The first two are databases; the dump is written inside the container and then copied out, which works the same in every shell.

```bash
mkdir -p backups

# 1. Application data: applicants, employers, statuses
docker compose exec postgres pg_dump -U n8n -Fc -d candidature -f /tmp/candidature.dump
docker compose cp postgres:/tmp/candidature.dump backups/candidature.dump

# 2. n8n's own data: workflows, encrypted credentials
docker compose exec postgres pg_dump -U n8n -Fc -d n8n -f /tmp/n8n.dump
docker compose cp postgres:/tmp/n8n.dump backups/n8n.dump

docker compose exec postgres rm /tmp/candidature.dump /tmp/n8n.dump
```

3. **`.env`**, kept somewhere private. It holds `N8N_ENCRYPTION_KEY`; without that exact key the credentials in the n8n backup cannot be decrypted.
4. **The `assets/` folder**: letter template, email text, CV, declaration.

The `backups/` folder is ignored by Git. Keep the dumps private and off the repository: they contain every employer contact. Generated letters (the `jobs` volume) can be rebuilt and do not need a backup.

### Restore

Restoring replaces what is in the database. Stop n8n first so no workflow runs during the restore.

```bash
docker compose stop n8n

docker compose cp backups/candidature.dump postgres:/tmp/candidature.dump
docker compose exec postgres pg_restore -U n8n -d candidature --clean --if-exists /tmp/candidature.dump

docker compose cp backups/n8n.dump postgres:/tmp/n8n.dump
docker compose exec postgres pg_restore -U n8n -d n8n --clean --if-exists /tmp/n8n.dump

docker compose exec postgres rm /tmp/candidature.dump /tmp/n8n.dump
docker compose start n8n
```

On a new server, create the empty database first with `docker compose exec postgres createdb -U n8n candidature`, and use the `.env` that belongs to the backup.

After restoring an older backup, look before letting it run: applications sent after the backup was taken are shown as `queued` or `awaiting_approval` again and would be sent a second time. Deactivate WF4, compare the queue with the mailbox's Sent folder, mark what was already sent as `sent` with the command from [An application stuck in `sending`](#an-application-stuck-in-sending) adapted to `status = 'queued'`, then reactivate WF4. The Telegram offset is restored too, so the bot may process again messages it had already handled.

Test a restore once on a spare machine before relying on the backups.
