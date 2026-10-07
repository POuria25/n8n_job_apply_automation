# Operations and limitations

[Back to README](../README.md)

The observations below come from reading the workflows. The claim, approval, and recovery rules described here are covered by the database tests in [`tests/`](../tests/); see [Testing](TESTING.md). Nothing here has been verified inside a running n8n instance.

## Workflow details

### WF1: Telegram interface

`Get offset` reads `bot_state.tg_offset`; `Get updates` polls Telegram; `Save offset` stores the largest received update ID plus one before downstream processing. `Applicants` and `Route` match the chat to an applicant, then route documents, bulk text, commands, dialogs, and approval callbacks.

Dialog state is held in `conversations`. Contact parsing recognizes email addresses, common address patterns, postcodes, and honorifics. These are heuristics: review the recap. Ordinary text containing a semicolon is routed to the bulk parser; explicitly recognized dialog commands have precedence.

Each approval button carries `action:targetId:draftVersion`. The version is `targets.draft_version`, which WF3 increments every time it drafts the letter, whether after **Refaire**, a manual retry, or an automatic one. `Apply decision` changes a row only when the target ID, applicant ID, `awaiting_approval` status, and version all match and the action is `approve`, `redo`, or `skip`. So a button works only on the preview it was sent with: after Refaire, the buttons of the older preview answer "Déjà traité ou introuvable", and a repeated tap on the current one does the same. Buttons sent before versions were added carry no version and count as version 0, so they still work on a preview that was sent before the upgrade and not redrafted since. WF1 and WF3 must be updated together, because one writes the version and the other checks it.

### WF2: MX checks

Up to ten `new` records are claimed as `checking`, and the claim time is stored in `claimed_at`. A record still in `checking` 15 minutes after it was claimed is treated as abandoned and claimed again. Google DNS is queried for MX records. The decision accepts an MX answer unless all MX answers are null MX (`0 .`). It writes `email_found` or `no_email` and warns on a failed check.

Only the company's email domain is checked; a separately supplied HR email domain is not independently checked. A pass does not establish mailbox existence. A failed check is not conclusive evidence that the domain cannot receive email.

### WF3: PDF drafting

One `email_found` row becomes `drafting`; the claim stores `claimed_at` and increments `draft_version`. A record still in `drafting` 15 minutes after it was claimed is claimed again. Applicant file paths supply the LaTeX skeleton and email sample. `Render` escapes the recipient block for LaTeX and substitutes the date. `Compile` writes and compiles `/data/jobs/<id>/letter.tex`.

On success the draft is saved and the status set to `awaiting_approval` **before** the preview is sent, so a button works from the moment it appears. If reading the PDF or sending the preview then fails, `Preview failed` puts the record back to `email_found` and WF3 drafts it again on a later run. After five drafts the record is set to `error` with "Aperçu non envoyé sur Telegram" instead, so one unreachable chat cannot block the queue. Compilation failures become `error` and are reported in the chat.

### WF4: SMTP delivery

`Pick one` claims the oldest approved `queued` record of each applicant whose count for the day is below `daily_limit`. The count is the records `sent` on the current database date plus those currently `sending`. The workflow then reads the letter, CV, and declaration and sends them to the company email plus the optional HR email.

The claim is one statement that locks the applicant row and the chosen record (`FOR UPDATE … SKIP LOCKED`) and re-checks `status = 'queued'` when it updates. Two overlapping runs therefore cannot claim the same application, and cannot both claim for the same applicant. The earlier query could: an overlapping run received the same row, which meant the same email twice.

Normal scheduled operation provides 20 slots each weekday: 08:00, 08:30, through 17:30, so the maximum per applicant is `min(daily_limit, 20)`.

One duplicate risk remains and cannot be removed from the database side: if the mail server accepts a message and the workflow then fails before `Mark sent`, the record stays in `sending` although the email went out. For that reason a `sending` record is never retried automatically; see the recovery section. `Mark sent` and `Mark send error` only act on a record that is still `sending`, so a late or repeated report cannot overwrite the other outcome.

## Diagnose before retrying

Run read-only checks against the application database:

```sql
SELECT status, count(*)
FROM targets
GROUP BY status
ORDER BY status;

SELECT id, company, status, error, approved_at, sent_at
FROM targets
WHERE status IN ('checking', 'drafting', 'sending', 'error')
ORDER BY id;

-- Sends that were interrupted and need a manual decision
SELECT id, company, email, claimed_at
FROM targets
WHERE status = 'sending' AND claimed_at < now() - interval '10 minutes';
```

`claimed_at` shows when a record was last claimed. `checking` and `drafting` recover by themselves after 15 minutes. A record in `sending` for more than a few minutes needs a decision from you: check running n8n executions and the mailbox first.

| Symptom | Check |
|---|---|
| Bot gives no response | Applicant allowlist, seeded offset, credentials, competing pollers or webhook, WF1 execution |
| Dialog stops | WF1 execution error and the matching `conversations` row |
| Employer marked `no_email` | DNS response and status; possible temporary DNS error or no-MX fallback case |
| Letter remains `drafting` | Asset paths, permissions, Tectonic availability, compilation log, Telegram preview failure |
| Application remains `sending` | Active execution, attachments, SMTP result, database update result |
| SMTP authentication fails | Full account address, app password, TLS configuration, selected credential |
| No email at the next slot | `queued` status, daily count, timezone, workflow activation, schedule |

Compilation logs are inside the n8n container at `/data/jobs/<id>/compile.log`. Treat logs and execution data as private: they may contain contact details, document text, or resolved request URLs.

## Recover a selected record

Pause affected schedules and wait for in-flight executions before changing state. Work on a known target ID, never all claimed rows at once. The following examples use fictional ID `42`; replace it after inspection.

`checking` and `drafting` records are taken back automatically after 15 minutes, so the two statements below are only needed to hurry that along, or for records claimed before `claimed_at` existed (their `claimed_at` is empty and they are not recovered automatically).

For a confirmed abandoned DNS check:

```sql
UPDATE targets
SET status = 'new'
WHERE id = 42 AND status = 'checking';
```

After repairing a drafting failure and confirming its cause:

```sql
UPDATE targets
SET status = 'email_found', error = NULL
WHERE id = 42 AND status IN ('drafting', 'error');
```

For sending failures, first determine whether SMTP accepted the message. Check provider logs and recipient evidence where available. SMTP submission may not create a copy in a mailbox's Sent folder, so absence there does not prove it was not sent. Requeue only a confirmed unsent application after fixing the failure; unresolved delivery uncertainty needs manual reconciliation to avoid duplicates.

To reset one dialog after confirming no execution is editing it:

```sql
UPDATE conversations
SET step = 'done', data = '{}'::jsonb, updated_at = now()
WHERE chat_id = 123456789;
```

The chat ID above is fictional. Do not publish query results containing actual applicants or employers.

## Known limitations and proposed improvements

| Observed behavior | Consequence | Proposed improvement |
|---|---|---|
| Offset is saved before processing | A failed downstream step can lose that batch; overlapping polling can also create races | Persist incoming updates and deduplicate by update ID before acknowledging progress |
| An interrupted send stays in `sending` | It is not retried, to avoid a duplicate, and it uses one place in the daily limit until resolved | Alert the applicant when a record has been `sending` for too long |
| DNS errors continue into the decision node | Temporary failures may become `no_email` | Separate transport errors and DNS status from definitive MX results |
| No implicit-MX fallback | A domain without explicit MX may be rejected even when SMTP fallback is possible | Implement the intended SMTP lookup policy, including A/AAAA fallback where appropriate |
| No reconciliation of an uncertain send | If SMTP accepts a message and the status update fails, only a manual check can tell whether it was sent | Record a message identifier per attempt and reconcile against the mailbox |
| Fixed sender, subject, and declaration | Multiple applicants cannot independently configure these | Add per-applicant configuration and credential routing |
| WF1 uses first-item assumptions in some branches | Simultaneous applicants may receive missing or mixed summaries | Group processing and replies by applicant/chat |
| Duplicate behavior depends on schema | Corrected employer data may conflict instead of updating | Review actual constraints and implement explicit correction/upsert behavior |
| Plain-string replacement of the recipient block | JavaScript replacement patterns in unusual names may corrupt output | Use `replace('<<RECIPIENT>>', () => recipient)` |
| Bulk email validation permits some malformed characters | Comma-separated query parameters can be affected | Tighten address validation and review parameter binding for the deployed node version |
| No bounce or reply processing | `sent` is not a delivery or response metric | Add independent delivery/reply handling if required |

`replied` and `stop` appear in the stats labels, but no supplied workflow sets them. `attempts` counts Refaire presses and enforces no limit; `draft_version` counts drafts and is what the buttons are checked against. The letter uses the drafting date, which may precede the sending date.

## Privacy, backups, and maintenance

The chat allowlist grants access by chat ID, not by an independently authenticated individual. Use private chats: everyone able to act in an allowed group chat may share that authority.

Base64 is encoding, not encryption or general sanitization. WF3's document body is passed as base64, but asset paths from `applicants` are interpolated into shell commands. Treat database write access and workflow editing as privileged. Keep templates trusted and paths controlled.

Back up the application database, n8n metadata database, encryption key, and private documents through a private backup process. Preserve the encryption key needed by the stored credentials. Do not publish dumps or credentials exports. Restore-test backups before depending on them, and define retention for generated letters, contacts, and execution data.

The Compose file prunes saved executions after 72 hours and disables successful-execution storage. This is not a guarantee that every log, failed execution, backup, or external service has no retained personal data.
