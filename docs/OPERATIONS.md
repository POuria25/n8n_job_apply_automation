# Operations and limitations

[Back to README](../README.md)

The observations below come from static workflow inspection. Suggested fixes are not implemented by this documentation update.

## Workflow details

### WF1: Telegram interface

`Get offset` reads `bot_state.tg_offset`; `Get updates` polls Telegram; `Save offset` stores the largest received update ID plus one before downstream processing. `Applicants` and `Route` match the chat to an applicant, then route documents, bulk text, commands, dialogs, and approval callbacks.

Dialog state is held in `conversations`. Contact parsing recognizes email addresses, common address patterns, postcodes, and honorifics. These are heuristics: review the recap. Ordinary text containing a semicolon is routed to the bulk parser; explicitly recognized dialog commands have precedence.

Approval updates are scoped to the target ID, applicant ID, and `awaiting_approval` status. `approve` moves the row to `queued`, `skip` to `skipped`, and the fallback action returns it to `email_found`. The code should explicitly validate allowed actions before applying a callback. A repeated approval normally cannot change a row that has already left `awaiting_approval`.

### WF2: MX checks

Up to ten `new` records are claimed as `checking`. Google DNS is queried for MX records. The decision accepts an MX answer unless all MX answers are null MX (`0 .`). It writes `email_found` or `no_email` and warns on a failed check.

Only the company's email domain is checked; a separately supplied HR email domain is not independently checked. A pass does not establish mailbox existence. A failed check is not conclusive evidence that the domain cannot receive email.

### WF3: PDF drafting

One `email_found` row becomes `drafting`. Applicant file paths supply the LaTeX skeleton and email sample. `Render` escapes the recipient block for LaTeX and substitutes the date. `Compile` writes and compiles `/data/jobs/<id>/letter.tex`.

The success path sends the PDF preview before changing the status to `awaiting_approval`. A sufficiently fast button press can therefore arrive before that status is saved. Compilation failures handled by the workflow become `error`; failures elsewhere may leave the row claimed.

### WF4: SMTP delivery

`Pick one` selects the oldest approved queued record per applicant, subject to the count of `sent` records for the current database date. The workflow reads the letter, CV, and declaration and sends them to the company email plus optional HR email.

Normal scheduled operation provides 20 slots each weekday: 08:00, 08:30, through 17:30. Under serial execution with no manual runs, the expected maximum per applicant is `min(daily_limit, 20)`. Manual runs, concurrent executions, and timing around failures mean this is not a guaranteed rate or quota boundary.

The claim query does not use the row-locking selection pattern used by WF2/WF3. Do not describe it as concurrency-safe or exactly-once. SMTP success followed by a failed database update can leave an email sent while its row still says `sending`.

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
```

A claim state does not by itself prove a record is abandoned. Check running n8n executions and logs first. There is no `claimed_at` field in the workflow queries, so elapsed claim time cannot be inferred reliably from them.

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
| No stale-claim recovery | Interrupted work can remain claimed indefinitely | Add claim timestamps, ownership, and stage-specific recovery |
| DNS errors continue into the decision node | Temporary failures may become `no_email` | Separate transport errors and DNS status from definitive MX results |
| No implicit-MX fallback | A domain without explicit MX may be rejected even when SMTP fallback is possible | Implement the intended SMTP lookup policy, including A/AAAA fallback where appropriate |
| Preview precedes approval-state update | Very fast approval can be ignored | Persist state before delivering an actionable preview, with failure recovery |
| Sending lacks atomic claim protection and delivery reconciliation | Concurrent runs or uncertain retries can duplicate email | Improve claim locking and preserve send-attempt/message identifiers; reconcile uncertain SMTP outcomes |
| Fixed sender, subject, and declaration | Multiple applicants cannot independently configure these | Add per-applicant configuration and credential routing |
| WF1 uses first-item assumptions in some branches | Simultaneous applicants may receive missing or mixed summaries | Group processing and replies by applicant/chat |
| Duplicate behavior depends on schema | Corrected employer data may conflict instead of updating | Review actual constraints and implement explicit correction/upsert behavior |
| Plain-string replacement of the recipient block | JavaScript replacement patterns in unusual names may corrupt output | Use `replace('<<RECIPIENT>>', () => recipient)` |
| Bulk email validation permits some malformed characters | Comma-separated query parameters can be affected | Tighten address validation and review parameter binding for the deployed node version |
| No bounce or reply processing | `sent` is not a delivery or response metric | Add independent delivery/reply handling if required |

`replied` and `stop` appear in the stats labels, but no supplied workflow sets them. `attempts` is incremented by Refaire; it does not enforce a retry limit. The letter uses the drafting date, which may precede the sending date.

## Privacy, backups, and maintenance

The chat allowlist grants access by chat ID, not by an independently authenticated individual. Use private chats: everyone able to act in an allowed group chat may share that authority.

Base64 is encoding, not encryption or general sanitization. WF3's document body is passed as base64, but asset paths from `applicants` are interpolated into shell commands. Treat database write access and workflow editing as privileged. Keep templates trusted and paths controlled.

Back up the application database, n8n metadata database, encryption key, and private documents through a private backup process. Preserve the encryption key needed by the stored credentials. Do not publish dumps or credentials exports. Restore-test backups before depending on them, and define retention for generated letters, contacts, and execution data.

The Compose file prunes saved executions after 72 hours and disables successful-execution storage. This is not a guarantee that every log, failed execution, backup, or external service has no retained personal data.
