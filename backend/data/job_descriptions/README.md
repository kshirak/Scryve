# Sample job descriptions

The files in this folder are reference inputs for the Phase 3 (Job
Intelligence) extractor. They are checked into the repo because they
are small, hand-written, and useful as smoke-test fixtures.

| File                                  | Purpose                                              |
| ------------------------------------- | ---------------------------------------------------- |
| `sample_python_django_developer.md`   | Mid-level backend role; exercises web framework tags |
| `sample_senior_ai_engineer.md`        | Senior AI/IR role; exercises domain + vector-DB tags |

Use them from a Python shell:

```python
from pathlib import Path
from app.intelligence.parsers.job_extractor import JobExtractor

text = Path("data/job_descriptions/sample_python_django_developer.md").read_text(encoding="utf-8")
extraction = JobExtractor().extract(text)
print(extraction.model_dump_json(indent=2))
```

Or through the HTTP API:

```bash
curl -X POST http://localhost:8000/api/v1/jobs/extract \
  -H "Content-Type: application/json" \
  -d "{\"description\": \"$(cat data/job_descriptions/sample_python_django_developer.md)\"}"
```
