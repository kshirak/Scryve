"""Loaders for job-description documents and curated job profiles.

Three input shapes are supported:

* Markdown / plain text (`.md`, `.txt`) — read verbatim.
* Microsoft Word (`.docx`) — extracted via `python-docx`, paragraphs joined
  with double newlines so the downstream parser can still detect headings.
* YAML (`.yaml`, `.yml`) — a pre-curated `JobProfile` is materialized
  directly, bypassing heuristic parsing entirely.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.core.logging import get_logger
from app.intelligence.domain import JobProfile

logger = get_logger(__name__)


def load_jd_text(path: Path | str) -> str:
    """Load the raw text of a job description from disk.

    Args:
        path: Path to a `.md`, `.txt`, or `.docx` file.

    Returns:
        Raw text content.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file extension is unsupported.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JD file not found: {path}")

    suffix = path.suffix.lower()
    if suffix in {".md", ".txt", ""}:
        return path.read_text(encoding="utf-8")
    if suffix == ".docx":
        return _read_docx(path)

    raise ValueError(
        f"Unsupported JD format '{suffix}'. Expected .md, .txt, or .docx."
    )


def _read_docx(path: Path) -> str:
    """Extract text content from a `.docx` document.

    Paragraph order is preserved and joined with double newlines so the
    downstream parser can still recognize headings and bullet structure.
    """
    try:
        from docx import Document  # local import keeps optional dep optional
    except ImportError as exc:  # pragma: no cover - exercised when dep missing
        raise ImportError(
            "Reading .docx job descriptions requires `python-docx`."
        ) from exc

    document = Document(str(path))
    paragraphs = [para.text for para in document.paragraphs if para.text]
    return "\n\n".join(paragraphs)


def load_job_profile_yaml(path: Path | str) -> JobProfile:
    """Load a pre-curated `JobProfile` from a YAML file.

    The YAML keys must match the `JobProfile` field names exactly.

    Args:
        path: Path to the YAML file.

    Returns:
        A fully constructed `JobProfile`.

    Raises:
        FileNotFoundError: If the file does not exist.
        pydantic.ValidationError: If the YAML cannot be coerced.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JobProfile YAML not found: {path}")

    with path.open("rt", encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}

    logger.info("jd.profile.loaded", path=str(path), role_title=data.get("role_title"))
    return JobProfile(**data)
