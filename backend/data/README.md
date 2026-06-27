# Data directory

Drop hackathon files here:

| File                                            | Tracked in git? | Notes                              |
| ----------------------------------------------- | --------------- | ---------------------------------- |
| `candidates.jsonl` / `candidates.jsonl.gz`      | No (gitignored) | 100k candidates, ~465 MB raw       |
| `candidate_schema.json`                         | Yes             | JSON Schema for validation         |
| `sample_candidates.json`                        | No              | 50 sample candidates               |
| `job_descriptions/redrob_senior_ai_engineer.md` | Yes             | JD source text (Markdown)          |
| `job_profiles/redrob_senior_ai_engineer.yaml`   | Yes             | Hand-curated structured JobProfile |

`.docx` JDs are also supported by the loader via `python-docx`.
