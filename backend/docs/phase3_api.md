# Phase 3 — Job Intelligence API

All endpoints are mounted under `${API_V1_PREFIX}` (defaults to
`/api/v1`). Responses are JSON; errors follow the standard
`ErrorResponse` envelope defined in `app/schemas/common.py`.

## Data model

A persisted job carries:

| Field                    | Type           | Description                                            |
| ------------------------ | -------------- | ------------------------------------------------------ |
| `id`                     | UUID           | Job primary key (the `job_id` referenced elsewhere).   |
| `title`                  | str            | Either the caller-supplied or extractor-inferred title.|
| `description`            | str            | The raw JD text.                                       |
| `role`                   | str?           | Role label (often equal to `title`).                   |
| `industry`               | str?           | Industry context, when surfaced by the JD.             |
| `experience_min_years`   | float?         | Minimum experience bound.                              |
| `experience_max_years`   | float?         | Maximum experience bound.                              |
| `experience_level`       | str?           | One of `Junior`, `Mid`, `Senior`, `Staff`, `Principal`.|
| `locations`              | list[str]      | Detected locations.                                    |
| `required_skills`        | list[str]      | Canonicalized must-have skills.                        |
| `preferred_skills`       | list[str]      | Canonicalized nice-to-have skills.                     |
| `soft_skills`            | list[str]      | Communication, Leadership, etc.                        |
| `programming_languages`  | list[str]      | Subset of skills in the `programming_language` bucket. |
| `tools_frameworks`       | list[str]      | Frameworks, libs, tools, databases, clouds.            |
| `domain_knowledge`       | list[str]      | ML, NLP, IR, Embeddings, RAG, Vector Search, ...       |
| `responsibilities`       | list[str]      | Verb-led bullets from the responsibilities section.    |
| `qualifications`         | list[str]      | Bullets under the qualifications section.              |
| `education_requirements` | list[str]      | Education-degree-bearing lines.                        |
| `disqualifiers`          | list[str]      | Explicit "do NOT want" lines.                          |
| `extracted_keywords`     | list[str]      | Lower-cased keyword bag for downstream BM25/hashing.   |
| `source_format`          | str            | `text`, `markdown`, `docx`, or `yaml`.                 |
| `raw_extraction`         | JSON           | Verbatim extractor output (auditing).                  |
| `created_at`             | datetime       | Persistence timestamp.                                 |
| `updated_at`             | datetime       | Last update timestamp.                                 |
| `embedding`              | JobEmbedding?  | Vector + metadata (model, dimension).                  |

## Endpoints

### POST `/api/v1/jobs/extract`

Run the Phase-3 extractor without persisting anything.

**Request**

```json
{
  "title": "Backend Developer",
  "description": "Looking for Python Django developer with PostgreSQL experience and REST API knowledge. 2-4 years experience required.",
  "generate_embedding": false
}
```

**Response (200)**

```json
{
  "title": "Backend Developer",
  "role": "Backend Developer",
  "experience_min_years": 2,
  "experience_max_years": 4,
  "experience_level": "Mid",
  "required_skills": ["Python", "Django", "PostgreSQL", "REST API"],
  "preferred_skills": [],
  "programming_languages": ["Python"],
  "tools_frameworks": ["Django", "PostgreSQL", "REST API"],
  "domain_knowledge": [],
  "responsibilities": [],
  "qualifications": [],
  "education_requirements": [],
  "disqualifiers": [],
  "extracted_keywords": ["python", "django", "postgresql", "rest api"],
  "soft_skills": [],
  "locations": []
}
```

### POST `/api/v1/jobs`

Extract, persist, and (optionally) embed a new job description.

**Request**

```json
{
  "title": "Senior AI Engineer",
  "description": "...full JD text in Markdown or plain text...",
  "source_format": "markdown",
  "generate_embedding": true
}
```

**Response (201)**

```json
{
  "id": "f8c7d4e2-5b1a-4f8c-9d1e-2b8a3c4d5e6f",
  "title": "Senior AI Engineer",
  "description": "...",
  "experience_min_years": 5,
  "experience_max_years": 9,
  "experience_level": "Senior",
  "required_skills": ["Python", "PyTorch", "FAISS", "Sentence-Transformers", "..."],
  "preferred_skills": ["LoRA", "QLoRA", "PEFT", "XGBoost", "..."],
  "...": "...",
  "embedding": {
    "id": "...",
    "job_id": "f8c7d4e2-...",
    "model_name": "hashing-v1",
    "dimension": 384,
    "created_at": "2026-06-28T10:00:00Z",
    "updated_at": "2026-06-28T10:00:00Z"
  }
}
```

### GET `/api/v1/jobs`

List recently created jobs (compact view).

Query params: `limit` (1-200, default 50), `offset` (>=0, default 0).

### GET `/api/v1/jobs/{job_id}`

Full job record including embedding metadata.

### GET `/api/v1/jobs/{job_id}/requirements`

Matching-ready view consumed by Phase 4 rankers:

```json
{
  "job_id": "f8c7d4e2-...",
  "title": "Senior AI Engineer",
  "experience_min_years": 5,
  "experience_max_years": 9,
  "experience_level": "Senior",
  "required_skills": ["Python", "PyTorch", "FAISS", "..."],
  "preferred_skills": ["LoRA", "..."],
  "soft_skills": ["Leadership", "Communication"],
  "programming_languages": ["Python"],
  "tools_frameworks": ["PyTorch", "FAISS", "..."],
  "domain_knowledge": ["Machine Learning", "Vector Search", "..."],
  "education_requirements": ["Master's degree in Computer Science"],
  "extracted_keywords": ["...", "..."],
  "disqualifiers": ["Pure research-only background ..."],
  "locations": ["Pune", "Noida"]
}
```

### GET `/api/v1/jobs/{job_id}/raw-extraction`

Verbatim extractor JSON (audit / debug).

### POST `/api/v1/jobs/{job_id}/embedding`

Regenerate the embedding vector. Useful after changing
`EMBEDDING_BACKEND` or `EMBEDDING_DIMENSION`.

**Response (200)**

```json
{
  "job_id": "f8c7d4e2-...",
  "model_name": "hashing-v1",
  "dimension": 384,
  "regenerated": true
}
```

### GET `/api/v1/jobs/{job_id}/embedding`

Return the embedding vector and metadata. Pass `include_vector=false`
to omit the vector payload (handy when you only need the metadata).

```json
{
  "id": "...",
  "job_id": "f8c7d4e2-...",
  "model_name": "hashing-v1",
  "dimension": 384,
  "vector": [0.0123, -0.0456, ...],
  "created_at": "...",
  "updated_at": "..."
}
```

## Programmatic usage

```python
from app.intelligence.parsers.job_extractor import extract_job_intelligence
from app.intelligence.embeddings import build_embedder
from app.intelligence.skills import SkillNormalizer

# Pure extraction
extraction = extract_job_intelligence(
    "Looking for Python Django developer with Postgres and REST APIs"
)
assert "PostgreSQL" in extraction.required_skills  # alias normalization
assert "REST API" in extraction.required_skills

# Embedding
embedder = build_embedder()
vec = embedder.embed("Senior AI engineer with vector search experience")
assert vec.dimension == 384
assert len(vec.vector) == 384

# Standalone normalization
normalizer = SkillNormalizer()
assert normalizer.normalize("Postgres") == "PostgreSQL"
assert normalizer.normalize("React.js") == "React"
assert normalizer.normalize("Py") == "Python"
```

## Skill normalization map

The full alias → canonical map lives in
`app/intelligence/skills/normalizer.py` (`SKILL_ALIASES`). Every
canonical skill is categorized via
`app/intelligence/skills/taxonomy.py` (`SKILL_TAXONOMY`). Both are
plain Python dictionaries — extend them at import time without
touching the call sites.
