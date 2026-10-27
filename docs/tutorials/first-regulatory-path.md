# Tutorial: plan your first regulatory path

In this tutorial you will start ComplianceOS on your machine, describe a satellite mission, and read
the regulatory path it produces. It takes about 15 minutes. No prior knowledge of licensing is
needed, but the terms are explained as they come up.

## Before you start

- Docker, with Compose v2 (`docker compose version` should print a version).
- A browser.

## 1. Start the stack

```bash
git clone https://github.com/esp75/complianceos.git
cd complianceos
docker compose up --build
```

The first build compiles the database's graph extension and takes a few minutes. When the logs
settle, open <http://localhost:3000>.

## 2. Open the sample mission

On the home page, choose **Open the sample mission**. It loads a sample mission with a complete
profile, so you can explore before entering your own data.

## 3. Read the roadmap

The roadmap lists every licence, authorisation and ITU filing the mission needs, grouped by country.
Pick one item and notice four things:

1. **Why it applies.** Each requirement is triggered by a rule that matches your mission profile.
2. **The authority.** The body that issues it, with its published contact channels.
3. **The cited law.** An excerpt quoted verbatim, a link to the official text, and the date it was
   last checked.
4. **Its obligations.** Renewals, milestones and reports that follow from it.

> The sample data is a research aid, not legal advice. Every record is marked `draft` until a
> licensing practitioner has reviewed it.

## 4. Read the timeline

Switch to the timeline. It works back from your launch date through prerequisites, so the ITU
publication appears before the notification that depends on it. The **critical path** is highlighted:
those items set your earliest launch date. Items with slack can slip without moving it.

Each duration is labelled as set in law, published practice, or an estimate. Check that label before
you rely on a date.

## 5. Define your own mission

Go to **New mission** (`/missions/new`). Enter your satellite count, orbit, the countries you will
serve, and your launch date. The live preview on the right shows how the roadmap changes as you type.

Choose **Create roadmap**. The mission is saved, and you can change its profile later from the edit
page; the roadmap is recalculated from the profile each time.

## 6. Track an application

On the mission's **Tracker** tab, each application moves through explicit states (for example from
preparing to submitted). Submission and grant dates re-date any obligations that depend on them. The
**Deadlines** and **Calendar** tabs show the dates, and the calendar exports to ICS for your diary.

## 7. Produce a brief and a dossier

The **Brief** tab contains the summary, critical path, risks, the recommended sequence, and questions
to ask each authority. The **Dossier** tab exports the same material as a PDF.

## What you learned

- A mission profile is decided once and drives every downstream view.
- Each requirement carries its own citation, so you can check the reasoning rather than trust it.
- Dates come from the prerequisite graph, not from guesses.

## Next steps

- Change one input in your mission and watch which items move: the
  [architecture explanation](../explanation/architecture.md) describes why.
- To correct a rule you know is wrong, see [how to add or correct a jurisdiction](../how-to/add-or-correct-a-jurisdiction.md).
- To sign your dossiers, see [how to enable signed dossiers](../how-to/enable-signed-dossiers.md).
