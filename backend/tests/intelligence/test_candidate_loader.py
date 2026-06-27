"""Tests for the streaming candidate loader."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from app.intelligence.loaders.candidate_loader import CandidateLoader


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def test_streams_jsonl_records(tmp_path, sample_record):
    path = tmp_path / "candidates.jsonl"
    _write_jsonl(path, [sample_record, sample_record])

    loader = CandidateLoader()
    records = list(loader.iter_raw(path))
    assert len(records) == 2


def test_skips_malformed_lines(tmp_path, sample_record):
    path = tmp_path / "candidates.jsonl"
    with path.open("wt", encoding="utf-8") as handle:
        handle.write(json.dumps(sample_record) + "\n")
        handle.write("not-json-at-all\n")
        handle.write(json.dumps(sample_record) + "\n")

    loader = CandidateLoader()
    assert loader.count(path) == 2


def test_reads_gzipped_jsonl(tmp_path, sample_record):
    path = tmp_path / "candidates.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(sample_record) + "\n")

    loader = CandidateLoader()
    candidates = list(loader.iter_candidates(path))
    assert len(candidates) == 1
    assert candidates[0].candidate_id == sample_record["candidate_id"]


def test_validates_against_schema(tmp_path, sample_record):
    schema_path = tmp_path / "schema.json"
    schema = {
        "type": "object",
        "required": ["candidate_id"],
        "properties": {"candidate_id": {"type": "string"}},
    }
    schema_path.write_text(json.dumps(schema))

    good = dict(sample_record)
    bad = {"name": "no id here"}

    data_path = tmp_path / "candidates.jsonl"
    _write_jsonl(data_path, [good, bad])

    loader = CandidateLoader(schema_path=schema_path)
    assert loader.count(data_path) == 1
