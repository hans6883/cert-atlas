# Contributing to Cert Atlas

Thanks for helping keep this dataset accurate and complete.

## Ways to contribute

### Update an existing exam

Exam details change -- new versions, updated objectives, price changes. To update:

1. Find the exam file in `data/{vendor}/{exam-id}.json`
2. Edit the relevant fields
3. Update the `source_url` if the official page has moved
4. Submit a PR with a link to the official source confirming the change

### Add a new exam

1. Create a JSON file following the schema in the README
2. Place it in `data/{vendor-slug}/` (create the directory if needed)
3. At minimum, include: `exam_id`, `exam_name`, `certifying_body`, `source_url`, and `domains`
4. Submit a PR with the official source URL

### Report an issue

Open a GitHub issue with:
- The exam name and ID
- What's incorrect or missing
- A link to the official source showing the correct information

## Guidelines

- Every addition or change must reference an official source (certifying body website, exam guide PDF, etc.)
- Do not include proprietary exam questions or answers
- Keep the JSON formatted with 2-space indentation
- Use the existing naming convention for `exam_id`: `{vendor}-{exam-name}-{code}`

## Running the export script

If you have access to the source database:

```bash
export BLUEPRINT_DB=/path/to/blueprint_registry.db
python scripts/export.py
```

This regenerates all files in `data/` from the database.
