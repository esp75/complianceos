# ComplianceOS documentation

The documentation follows the [Diátaxis](https://diataxis.fr/) framework. Each section answers a
different kind of need, so pick the one that matches what you are trying to do.

|  | **Studying** (acquisition) | **Working** (application) |
|---|---|---|
| **Practical** | [**Tutorials**](#tutorials): learn by doing, step by step | [**How-to guides**](#how-to-guides): solve one specific task |
| **Theoretical** | [**Explanation**](#explanation): why it is built this way | [**Reference**](#reference): precise facts to look up |

## Tutorials

Learning-oriented. Follow them from start to finish.

- [Plan your first regulatory path](tutorials/first-regulatory-path.md): run the planner locally,
  define a mission, and read the roadmap, timeline and brief.

## How-to guides

Task-oriented. Assume you know what you want to achieve.

- [Run the test suites](how-to/run-tests.md)
- [Add or correct a jurisdiction's rules](how-to/add-or-correct-a-jurisdiction.md)
- [Enable signed dossiers](how-to/enable-signed-dossiers.md)
- [Enable Claude-written summaries](how-to/enable-claude-summaries.md)

## Reference

Information-oriented. Look things up here.

- [HTTP API](reference/api.md): the planner endpoints and where the full OpenAPI schema lives
- [Configuration](reference/configuration.md): environment variables and what they control
- [Knowledge pack](reference/knowledge-pack.md): the YAML format for licences, rules and citations
- [Coverage](reference/coverage.md): which jurisdictions and instruments are modelled today
- [Licence matrix](license-matrix.md): licences of the code, data and vendored dependencies

## Explanation

Understanding-oriented. Read these to understand the design.

- [Architecture](explanation/architecture.md): how the planner turns a mission into a roadmap
- [Why every requirement cites the law](explanation/why-cited-law.md)
- [Trust, signing and the threat model](explanation/trust-and-signing.md)
- [Decisions (ADRs)](explanation/decisions.md): an index of the architecture decision records
- [Engineering log](explanation/engineering-log.md): how the project was built, milestone by milestone
- [Earlier architecture (v0.1 layers)](explanation/earlier-architecture.md): what the `layers/` folder is and why it is still here
