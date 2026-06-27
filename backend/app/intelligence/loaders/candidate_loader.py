"""Streaming loader for the 100k-candidate JSONL dataset.

The loader is designed around three constraints from the hackathon spec:

* The dataset is large (~465 MB uncompressed). Records are streamed line by
  line so the ranker never holds all 100k in memory at once.
* Records may be malformed. The loader skips them and emits a structured
  log entry; one bad line never aborts the pipeline.
* A JSON Schema is provided. When the schema path is supplied, every
  record is validated against it before being parsed.

Compute footprint is intentionally tiny: a single open file handle, one
`jsonschema` validator instance, and one dict per iteration.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, IO

import jsonschema
from jsonschema.protocols import Validator

from app.core.logging import get_logger
from app.intelligence.domain import Candidate
from app.intelligence.parsers.candidate_parser import CandidateParser

logger = get_logger(__name__)


@contextmanager
def _open_jsonl(path: Path) -> Iterator[IO[str]]:
    """Open a `.jsonl` or `.jsonl.gz` file as a text stream.

    Args:
        path: File path; gzip is detected by suffix.

    Yields:
        A text file handle in read mode.
    """
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            yield handle  # type: ignore[misc]
    else:
        with path.open("rt", encoding="utf-8") as handle:
            yield handle


def _build_validator(schema_path: Path | None) -> Validator | None:
    """Build a JSON Schema validator from the given path, if provided.

    Args:
        schema_path: Path to a JSON Schema document.

    Returns:
        A `jsonschema` validator, or `None` when no schema is provided or
        the file is missing.
    """
    if schema_path is None or not schema_path.exists():
        return None
    with schema_path.open("rt", encoding="utf-8") as handle:
        schema = json.load(handle)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    return validator_cls(schema)


class CandidateLoader:
    """Streams candidate records from a JSONL file with optional validation.

    Attributes:
        schema_path: Optional path to a JSON Schema for record validation.
        strict: When True, the loader raises on schema violations instead
            of skipping and logging. Defaults to False (lenient streaming).
        parser: The `CandidateParser` used to materialize `Candidate`
            objects.
    """

    def __init__(
        self,
        schema_path: Path | None = None,
        *,
        strict: bool = False,
        parser: CandidateParser | None = None,
    ) -> None:
        self.schema_path = schema_path
        self.strict = strict
        self.parser = parser or CandidateParser()
        self._validator = _build_validator(schema_path)
        if schema_path and self._validator is None:
            logger.warning(
                "loader.schema.missing",
                path=str(schema_path),
                message="Schema file not found; records will not be validated.",
            )

    # ------------------------------------------------------------------
    # Streaming primitives
    # ------------------------------------------------------------------
    def iter_raw(self, path: Path) -> Iterator[dict[str, Any]]:
        """Yield raw record dicts, skipping malformed lines.

        Args:
            path: JSONL or `.jsonl.gz` file path.

        Yields:
            Validated raw dictionaries (one per record).
        """
        path = Path(path)
        with _open_jsonl(path) as handle:
            for line_no, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning(
                        "loader.json.malformed",
                        line_no=line_no,
                        error=str(exc),
                    )
                    continue
                if not self._validate(record, line_no):
                    continue
                yield record

    def iter_candidates(self, path: Path) -> Iterator[Candidate]:
        """Yield parsed `Candidate` objects from a JSONL file.

        Args:
            path: JSONL or `.jsonl.gz` file path.

        Yields:
            `Candidate` aggregates ready for feature engineering.
        """
        for record in self.iter_raw(path):
            try:
                yield self.parser.parse(record)
            except Exception:  # noqa: BLE001 - parser errors are logged, not fatal
                logger.exception(
                    "loader.parse.failed",
                    candidate_id=record.get("candidate_id"),
                )
                continue

    def count(self, path: Path) -> int:
        """Count the number of *valid* records in a JSONL file.

        Useful for smoke tests; does not parse records, just validates.

        Args:
            path: JSONL or `.jsonl.gz` file path.

        Returns:
            Number of records that passed JSON + schema validation.
        """
        total = 0
        for _ in self.iter_raw(path):
            total += 1
        return total

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _validate(self, record: dict[str, Any], line_no: int) -> bool:
        """Validate a single record. Logs and returns False on failure."""
        if self._validator is None:
            return True
        errors = list(self._validator.iter_errors(record))
        if not errors:
            return True
        sample = [e.message for e in errors[:3]]
        logger.warning(
            "loader.schema.invalid",
            line_no=line_no,
            candidate_id=record.get("candidate_id"),
            error_count=len(errors),
            errors=sample,
        )
        if self.strict:
            raise jsonschema.ValidationError(
                f"Schema validation failed for line {line_no}: {sample}"
            )
        return False
