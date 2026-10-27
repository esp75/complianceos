# How to add or correct a jurisdiction's rules

Licensing data lives in [`knowledge/`](../../knowledge/README.md) as YAML. You do not need to write
code to fix a rule or add a licence.

## Before you start

- Read the [ground rules](../../knowledge/README.md#ground-rules). The short version: quote the law
  verbatim, link the official source, and never guess a citation.
- Find the file you need: `knowledge/jurisdictions/<id>/licenses/<licence>.yaml`.

## Steps

1. **Edit the licence file.** Change the field you need. The field table is in
   [the knowledge README](../../knowledge/README.md#a-licence-file-in-short), and the JSON Schema in
   `knowledge/schema/` gives editor autocompletion.
2. **Cite the source.** Put the exact text in `excerpt`, the official URL in `url`, and today's date
   in `retrieved`. For non-English texts add `excerpt_en` and mark it as an unofficial translation.
3. **Set the duration basis honestly.** Use `statutory` when a time limit is in law, `practice` when
   it comes from published guidance, and `estimate` otherwise.
4. **Validate.**

   ```bash
   cd app && uv run python -m app.planner.knowledge validate
   ```

5. **Check the result in the planner.** Run the API and web app
   ([see the tutorial](../tutorials/first-regulatory-path.md)), open a mission in that country, and
   confirm the item's reasons and dates read correctly.
6. **Open a pull request.** Describe the source you checked and what changed. Use the
   [data correction](../../.github/ISSUE_TEMPLATE/data-correction.yml) template if you are reporting
   rather than fixing.

## Adding a new country

Create `knowledge/jurisdictions/<id>/` with a `jurisdiction.yaml` (authorities and their official
contact channels) and a `licenses/` folder. Then add the country's records to
[`knowledge/VERIFICATION.md`](../../knowledge/VERIFICATION.md) and note what still needs a licensing
practitioner's review. Records stay `draft` until one has reviewed them.
