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

The timeline is at the top of the **Roadmap** tab. It is a Gantt chart: each bar is one licence, and
the light part is preparation, the dark part is authority review. It works back from your launch date
through prerequisites, so the ITU publication appears before the notification that depends on it.

Items marked with a blue dot are on the **critical path**: they set your earliest launch date. Items
with slack can slip without moving it. The legend under the chart explains the colours.

Each duration is labelled as set in law, published practice, or an estimate. Check that label before
you rely on a date.

## 5. Define your own mission

Go to **Missions → New mission** (`/missions/new`). The wizard has four steps:

1. **Operator:** mission name, operator name, and the country where the operator is established.
2. **Spacecraft & orbit:** orbit type, number of satellites and altitude.
3. **Spectrum & services:** the services you provide (for example Earth observation) and frequency bands.
4. **Markets & launch:** the countries you will serve, the launch site country, and the target launch date.

Use **Next** and **Back** to move between steps. On the last step, choose **Create roadmap**. The
mission is saved and its roadmap is calculated straight away. Use **Edit mission** later to change any
of these answers.

## 6. Track an application

Open the **Tracker** tab. It shows the applications you have not yet tracked, and three columns:
**To do**, **With the authority** and **Decided**. Choose **Track all** to add every item to
**To do**. Each card shows its status (for example *Not started*)
and the date you should start preparing.

Once an application is with the authority or decided, record the real submission and grant dates. Those
dates move the obligations that depend on them. The **Deadlines** tab lists every date, and **Calendar**
(in the mission header) exports them to ICS for your diary.

## 7. Produce a brief and a dossier

The **Brief** tab has the summary, critical path, risks and the questions to ask each authority. Each
legal statement in it links to the law. To export the same material as a PDF, use **Download dossier
(PDF)** in the mission header.

## Troubleshooting

- **`docker compose up` fails with `docker-credential-desktop: not found`.** Your Docker config still
  names a credential helper from a previous install. Remove the `credsStore` line from `~/.docker/config.json`.
- **The stack is up but `localhost:3000` refuses the connection.** The Docker socket may have died while
  colima reported running. Run `colima restart`, then `docker compose up -d`.
- **The `core` image crash-loops on Apple Silicon.** Start colima with Rosetta: `colima start --vm-type vz --vz-rosetta`.

## What you learned

- A mission profile is decided once and drives every downstream view.
- Each requirement carries its own citation, so you can check the reasoning rather than trust it.
- Dates come from the prerequisite graph, not from guesses.

## Next steps

- Change one input in your mission and watch which items move: the
  [architecture explanation](../explanation/architecture.md) describes why.
- To correct a rule you know is wrong, see [how to add or correct a jurisdiction](../how-to/add-or-correct-a-jurisdiction.md).
- To sign your dossiers, see [how to enable signed dossiers](../how-to/enable-signed-dossiers.md).
