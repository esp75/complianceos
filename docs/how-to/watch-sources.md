# How to run the Watch

The Watch re-checks every public source the knowledge pack cites and records what changed. It
tells you which of your tracked applications cite a changed source. It does not tell you what the
change means: re-verify the cited provision before you rely on it.

The Watch needs Postgres. Set `CELESTIA_PLANNER_DSN`, or leave it empty to use `CELESTIA_KG_DSN`.

## 1. Take a baseline

The first check only records what each source says now. Nothing is reported as changed on the first
run, so run it once before you schedule it:

```bash
cd app
uv run python -m app.planner.watch run
```

Each line of output is one source. `unsupported` means the Watch cannot read the source (a scanned
PDF, say), and `unreachable` means the source did not answer. PDFs with text are read.

## 2. Schedule it

With `docker compose up`, the `watch` service already does this: it runs the check once a day
(`WATCH_INTERVAL_SECONDS` changes the pace) and sends email when SMTP is configured in `.env`.
Without compose, run it from cron:

**Who gets the email.** Each workspace sets its own recipients on the Workspace page (or
`PUT /alerts/recipients`): its digest goes only to them. A workspace with none set falls back to
`CELESTIA_ALERT_RECIPIENTS`, so on a shared deployment have every client set their own list.

```cron
30 6 * * *  cd /path/to/complianceOSv0.2/app && uv run python -m app.planner.watch run >> /var/log/watch.log 2>&1
```

## 3. Get an email

Add `--alert` to send one digest per run, only when a change touches a tracked application. Use an
EU-hosted SMTP relay and set these in the environment (never commit them):

```bash
CELESTIA_SMTP_HOST=smtp.example.eu
CELESTIA_SMTP_PORT=587            # starttls; use CELESTIA_SMTP_SECURITY=ssl for port 465
CELESTIA_SMTP_USER=...  CELESTIA_SMTP_PASSWORD=...
CELESTIA_ALERT_FROM=watch@example.eu
CELESTIA_ALERT_RECIPIENTS=you@example.eu,colleague@example.eu   # fallback only, see below
CELESTIA_PUBLIC_WEB_URL=https://planner.example.eu   # optional, for the link in the email
```

```cron
30 6 * * *  cd /path/to/complianceOSv0.2/app && uv run python -m app.planner.watch run --alert >> /var/log/watch.log 2>&1
```

If you also set `CELESTIA_ANTHROPIC_API_KEY`, changed pages get an advisory label and one-line
summary from Claude on the Anthropic EU endpoint. It is labelled unverified in the app and the
email, and the Watch's advice stays "re-verify".

## 4. See what changed

```bash
uv run python -m app.planner.watch changes
```

Or open a mission's **Watch** tab in the web app, which lists each change with the applications that
cite the source.

## What to expect

- **Some sources are not watched.** Légifrance (the French codes) blocks automated requests, so
  those four citations show as `unreachable` and are not compared. Check them by hand when a date
  matters. See [ADR-0019](../../adr/0019-the-watch-v0.md) and [ADR-0020](../../adr/0020-the-watch-alerts-pdf-feeds-triage.md).
- **Feeds report new publications.** GB and US have an official feed listed in the pack. A
  "New publication" is an entry matching the feed's keywords; read it to see if it applies.
- **Outages are not changes.** A source that goes down is reported once as unreachable, and its last
  good text is kept, so the next successful check compares with it.
- **Changes before the first run are not detected.** The baseline is the Watch's own first check.
