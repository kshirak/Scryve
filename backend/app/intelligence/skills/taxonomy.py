"""Curated skill taxonomy used by the job extractor and normalizer.

The taxonomy is intentionally hand-curated rather than ML-derived: at the
hackathon scale (~100k candidates, hundreds of JDs) a tight, recruiter-
reviewable list beats noisy auto-extraction. Each canonical skill is
mapped to a single :class:`SkillCategory` so downstream code can bucket
extracted skills into ``programming_languages``, ``tools_frameworks``,
``domain_knowledge``, etc.

Both this taxonomy and ``SKILL_ALIASES`` (in :mod:`normalizer`) are
exposed as plain dictionaries so consumers can extend them at import
time without monkey-patching.
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class SkillCategory(str, Enum):
    """High-level bucket for a normalized skill."""

    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    LIBRARY = "library"
    TOOL = "tool"
    DATABASE = "database"
    CLOUD = "cloud"
    DOMAIN = "domain"
    SOFT_SKILL = "soft_skill"
    METHODOLOGY = "methodology"
    OTHER = "other"


# Canonical skill name → category. The canonical name is what the
# normalizer emits; lookups are case-insensitive.
SKILL_TAXONOMY: Final[dict[str, SkillCategory]] = {
    # --- Programming languages ---
    "Python": SkillCategory.PROGRAMMING_LANGUAGE,
    "Java": SkillCategory.PROGRAMMING_LANGUAGE,
    "JavaScript": SkillCategory.PROGRAMMING_LANGUAGE,
    "TypeScript": SkillCategory.PROGRAMMING_LANGUAGE,
    "C++": SkillCategory.PROGRAMMING_LANGUAGE,
    "C#": SkillCategory.PROGRAMMING_LANGUAGE,
    "C": SkillCategory.PROGRAMMING_LANGUAGE,
    "Go": SkillCategory.PROGRAMMING_LANGUAGE,
    "Rust": SkillCategory.PROGRAMMING_LANGUAGE,
    "Ruby": SkillCategory.PROGRAMMING_LANGUAGE,
    "PHP": SkillCategory.PROGRAMMING_LANGUAGE,
    "Scala": SkillCategory.PROGRAMMING_LANGUAGE,
    "Kotlin": SkillCategory.PROGRAMMING_LANGUAGE,
    "Swift": SkillCategory.PROGRAMMING_LANGUAGE,
    "R": SkillCategory.PROGRAMMING_LANGUAGE,
    "SQL": SkillCategory.PROGRAMMING_LANGUAGE,
    "Bash": SkillCategory.PROGRAMMING_LANGUAGE,
    "Perl": SkillCategory.PROGRAMMING_LANGUAGE,

    # --- Web / app frameworks ---
    "Django": SkillCategory.FRAMEWORK,
    "Flask": SkillCategory.FRAMEWORK,
    "FastAPI": SkillCategory.FRAMEWORK,
    "Spring Boot": SkillCategory.FRAMEWORK,
    "Express.js": SkillCategory.FRAMEWORK,
    "React": SkillCategory.FRAMEWORK,
    "Vue.js": SkillCategory.FRAMEWORK,
    "Angular": SkillCategory.FRAMEWORK,
    "Next.js": SkillCategory.FRAMEWORK,
    "Nest.js": SkillCategory.FRAMEWORK,
    "Ruby on Rails": SkillCategory.FRAMEWORK,
    "Laravel": SkillCategory.FRAMEWORK,
    ".NET": SkillCategory.FRAMEWORK,
    "ASP.NET": SkillCategory.FRAMEWORK,
    "Svelte": SkillCategory.FRAMEWORK,

    # --- ML / AI frameworks & libraries ---
    "TensorFlow": SkillCategory.FRAMEWORK,
    "PyTorch": SkillCategory.FRAMEWORK,
    "Keras": SkillCategory.FRAMEWORK,
    "scikit-learn": SkillCategory.LIBRARY,
    "XGBoost": SkillCategory.LIBRARY,
    "LightGBM": SkillCategory.LIBRARY,
    "Hugging Face Transformers": SkillCategory.LIBRARY,
    "LangChain": SkillCategory.LIBRARY,
    "LlamaIndex": SkillCategory.LIBRARY,
    "spaCy": SkillCategory.LIBRARY,
    "NLTK": SkillCategory.LIBRARY,
    "OpenCV": SkillCategory.LIBRARY,
    "Pandas": SkillCategory.LIBRARY,
    "NumPy": SkillCategory.LIBRARY,
    "Sentence-Transformers": SkillCategory.LIBRARY,

    # --- Vector / search / databases ---
    "FAISS": SkillCategory.TOOL,
    "Pinecone": SkillCategory.DATABASE,
    "Weaviate": SkillCategory.DATABASE,
    "Qdrant": SkillCategory.DATABASE,
    "Milvus": SkillCategory.DATABASE,
    "Elasticsearch": SkillCategory.DATABASE,
    "OpenSearch": SkillCategory.DATABASE,
    "PostgreSQL": SkillCategory.DATABASE,
    "MySQL": SkillCategory.DATABASE,
    "MongoDB": SkillCategory.DATABASE,
    "Redis": SkillCategory.DATABASE,
    "Cassandra": SkillCategory.DATABASE,
    "DynamoDB": SkillCategory.DATABASE,
    "Snowflake": SkillCategory.DATABASE,
    "BigQuery": SkillCategory.DATABASE,

    # --- Cloud providers ---
    "AWS": SkillCategory.CLOUD,
    "GCP": SkillCategory.CLOUD,
    "Azure": SkillCategory.CLOUD,

    # --- DevOps / tools ---
    "Docker": SkillCategory.TOOL,
    "Kubernetes": SkillCategory.TOOL,
    "Terraform": SkillCategory.TOOL,
    "Git": SkillCategory.TOOL,
    "GitHub Actions": SkillCategory.TOOL,
    "Jenkins": SkillCategory.TOOL,
    "Airflow": SkillCategory.TOOL,
    "Kafka": SkillCategory.TOOL,
    "RabbitMQ": SkillCategory.TOOL,
    "Spark": SkillCategory.TOOL,
    "Hadoop": SkillCategory.TOOL,
    "REST API": SkillCategory.TOOL,
    "GraphQL": SkillCategory.TOOL,
    "gRPC": SkillCategory.TOOL,

    # --- Methodologies ---
    "Agile": SkillCategory.METHODOLOGY,
    "Scrum": SkillCategory.METHODOLOGY,
    "Kanban": SkillCategory.METHODOLOGY,
    "TDD": SkillCategory.METHODOLOGY,
    "CI/CD": SkillCategory.METHODOLOGY,

    # --- Domain knowledge (AI / IR specific to the hackathon focus) ---
    "Machine Learning": SkillCategory.DOMAIN,
    "Deep Learning": SkillCategory.DOMAIN,
    "Natural Language Processing": SkillCategory.DOMAIN,
    "Computer Vision": SkillCategory.DOMAIN,
    "Information Retrieval": SkillCategory.DOMAIN,
    "Recommendation Systems": SkillCategory.DOMAIN,
    "Learning to Rank": SkillCategory.DOMAIN,
    "Embeddings": SkillCategory.DOMAIN,
    "Vector Search": SkillCategory.DOMAIN,
    "Hybrid Search": SkillCategory.DOMAIN,
    "RAG": SkillCategory.DOMAIN,
    "LLM Fine-tuning": SkillCategory.DOMAIN,
    "LoRA": SkillCategory.DOMAIN,
    "QLoRA": SkillCategory.DOMAIN,
    "PEFT": SkillCategory.DOMAIN,
    "MLOps": SkillCategory.DOMAIN,
    "Data Engineering": SkillCategory.DOMAIN,
    "Statistics": SkillCategory.DOMAIN,
    "A/B Testing": SkillCategory.DOMAIN,
}


# Soft-skill keywords used both for extraction and matching. Keys are the
# canonical names; values are the substrings to search for in the JD.
SOFT_SKILL_KEYWORDS: Final[dict[str, tuple[str, ...]]] = {
    "Communication": ("communication", "communicate"),
    "Leadership": ("leadership", "lead a team", "mentor", "mentoring", "mentorship"),
    "Teamwork": ("teamwork", "collaboration", "collaborate", "cross-functional"),
    "Problem Solving": ("problem solving", "problem-solving", "analytical thinking"),
    "Adaptability": ("adaptability", "adaptable", "fast-paced"),
    "Ownership": ("ownership", "self-driven", "self-starter", "self starter"),
    "Critical Thinking": ("critical thinking",),
    "Time Management": ("time management", "prioritization"),
    "Stakeholder Management": ("stakeholder", "stakeholder management"),
    "Curiosity": ("curiosity", "curious", "growth mindset"),
}
