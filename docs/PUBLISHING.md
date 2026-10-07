# Publishing on GitHub

[Back to README](../README.md)

Publish a clean source copy. Keep the live VPS configuration, documents, database, and backups private. The repository's current visibility and Git history have not been inspected.

## Prepare the public files

1. Keep one reviewed copy of WF1–WF4 under `workflows/`, using the filenames in the README. Exclude full-instance backups and alternate patched copies unless reviewed separately.
2. Include the supplied Dockerfile and Compose file, this README, and the documentation folder.
3. Include `.env.example` with placeholders only. Do not include the working `.env`, even if it is in a renamed file such as `.env(1)`.
4. Export workflows with `active` set to `false` and empty `pinData`. Remove `staticData`, top-level `id`, `versionId`, instance `meta`, and node `webhookId` fields from the public copies. Preserve structural node IDs and connections.
5. Remove each node's entire `credentials` property. Users will select their own credentials after importing. Blank strings or spaces are not useful credential references.
6. Replace the sender email with a neutral placeholder, or use the documented `SENDER_EMAIL` variant consistently across WF4, Compose, and `.env.example`.
7. Inspect every node parameter, code string, URL, sample, screenshot, and document for personal information or pasted secrets. Metadata removal alone is not a secret scan.

Credential names and IDs are references, not login secrets. They are removed for portability. Actual passwords or API keys pasted into node parameters are different: they can be exposed in exported JSON.

The reviewed pipeline has no DeepSeek or OpenAI integration. Do not state that unreviewed instance backups or other workflows are equally free of secrets.

## Suggested `.gitignore`

```gitignore
# Real environment files, including renamed uploads
.env*
!.env.example
*.env

# Private documents and generated files
assets/
data/
jobs/
backups/
*.pdf
*.log
*.dump
*.backup
*.sqlite*

# Local service data
.n8n/
n8n_data/
pg_data/
tectonic_cache/

# Credential exports and unrelated instance backups
credentials*.json
workflows-backup*.json
```

Do not blanket-ignore all `.sql` or `.tex` files: a reviewed schema-only migration and fictional example template can be useful public source. Keep real database dumps and personalized templates in ignored private directories and inspect any new SQL or LaTeX source before staging.

`.gitignore` does not remove tracked files or past commits. A renamed or compressed sensitive file can also escape filename-based patterns.

## Review the staged files

Use a fresh directory containing only the reviewed public source. Do not copy the old `.git` directory if the goal is a new, clean repository.

```bash
git init -b main
git add README.md docs/ workflows/ Dockerfile docker-compose.yml .env.example .gitignore
git status --short
git diff --cached --stat
git diff --cached
```

Review the full staged diff locally. A supplementary search using ripgrep can flag files for inspection without printing matching secret values:

```bash
rg -l --hidden -i -g '!.git/**' -g '!.env' \
  'password|secret|api[_-]?key|authorization|bearer|[0-9]{6,}:[A-Za-z0-9_-]{20,}' .
```

Configuration variable names and documentation will produce legitimate matches. This search is not comprehensive and a clean result does not prove the repository has no secrets. Review changed content and use an appropriate secret scanner as part of your publishing process.

Once the staged files have been reviewed:

```bash
git commit -m "Publish sanitized job application workflows and documentation"
```

Create a new empty GitHub repository named `n8n_job_apply_automation` in your account. To use the commands below, replace `YOUR_USERNAME` and ensure GitHub authentication is configured:

```bash
git remote add origin https://github.com/YOUR_USERNAME/n8n_job_apply_automation.git
git push -u origin main
```

These instructions target a **new empty repository**. For an existing repository, inspect its history and remote first; do not force-push as a routine publishing step. Upload the extracted project files, not just a ZIP, so GitHub renders the README and exposes the source.

## If sensitive data was already committed

Changing the latest file does not remove earlier versions. For a published secret, revoke or rotate the affected credential first, then follow GitHub's guidance on history cleanup where needed. Coordinate history changes with collaborators. Do not casually replace an n8n encryption key: plan migration so existing stored credentials remain recoverable.

A new clean repository does not remove sensitive content from an older repository, clone, fork, release attachment, issue, or screenshot. Review those separately if they exist. Do not assume a private repository has never been accessed or copied.

## Repository presentation

Suggested description:

> Self-hosted n8n workflows for Telegram-guided job applications, LaTeX cover letters, manual approval, and scheduled SMTP delivery.

Suggested topics: `n8n`, `workflow-automation`, `telegram-bot`, `postgresql`, `docker`, `latex`, `job-applications`.

Add screenshots only after removing personal addresses, names, chat IDs, documents, and tokens. Label the project as template-based automation. Do not claim AI personalization, confirmed delivery, or production-grade reliability.

If you want to grant reuse rights, choose a license you intend to apply and add its actual `LICENSE` file. This documentation update does not choose a license on your behalf.

## References

- [GitHub: Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [GitHub: Deleting files and the persistence of Git history](https://docs.github.com/en/repositories/working-with-files/managing-files/deleting-files-in-a-repository)
