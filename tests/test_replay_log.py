"""Tests for the deterministic-replay log (worker/replay_log.py).

Hermetic: no DB, no network. Uses tmp_path + ONELIVE_REPLAY_LOG_DIR to avoid
touching the repo's real var/replay directory.
"""
import json
import os
import stat

import pytest

from worker.replay_log import (
    ReplayLogWriteError,
    ReplayRecord,
    canonical_digest,
    log_step,
    new_run_id,
)


def _record(run_id: str, **overrides) -> ReplayRecord:
    base = dict(
        run_id=run_id,
        ts="2026-07-11T00:00:00+00:00",
        source_id="src-1",
        source_name="Test Source",
        stage="fetch",
        inputs_digest=canonical_digest({"url": "https://example.com"}),
        outputs_digest=canonical_digest({"status": "ok"}),
        decision="ok",
        detail="fetched fine",
    )
    base.update(overrides)
    return ReplayRecord(**base)


def test_new_run_id_is_unique_and_stringy():
    a, b = new_run_id(), new_run_id()
    assert isinstance(a, str) and isinstance(b, str)
    assert a != b


def test_canonical_digest_stable_for_same_input():
    payload = {"b": 2, "a": 1, "nested": {"z": 9, "y": 8}}
    assert canonical_digest(payload) == canonical_digest(payload)
    # Key order must not matter.
    reordered = {"nested": {"y": 8, "z": 9}, "a": 1, "b": 2}
    assert canonical_digest(payload) == canonical_digest(reordered)


def test_canonical_digest_differs_for_different_input():
    assert canonical_digest({"a": 1}) != canonical_digest({"a": 2})


def test_log_step_writes_one_jsonl_line(tmp_path, monkeypatch):
    monkeypatch.setenv("ONELIVE_REPLAY_LOG_DIR", str(tmp_path))
    run_id = new_run_id()
    log_step(_record(run_id))

    path = tmp_path / f"{run_id}.jsonl"
    assert path.exists()
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["run_id"] == run_id
    assert parsed["stage"] == "fetch"
    assert parsed["decision"] == "ok"


def test_log_step_appends_multiple_records(tmp_path, monkeypatch):
    monkeypatch.setenv("ONELIVE_REPLAY_LOG_DIR", str(tmp_path))
    run_id = new_run_id()
    log_step(_record(run_id, stage="fetch"))
    log_step(_record(run_id, stage="extract", decision="extracted"))

    path = tmp_path / f"{run_id}.jsonl"
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["stage"] == "fetch"
    assert json.loads(lines[1])["stage"] == "extract"


def test_digests_stable_for_same_logical_input_across_records(tmp_path, monkeypatch):
    monkeypatch.setenv("ONELIVE_REPLAY_LOG_DIR", str(tmp_path))
    run_id = new_run_id()
    same_payload = {"candidate_id": "abc-123"}
    log_step(_record(run_id, stage="a", inputs_digest=canonical_digest(same_payload)))
    log_step(_record(run_id, stage="b", inputs_digest=canonical_digest(same_payload)))

    path = tmp_path / f"{run_id}.jsonl"
    lines = [json.loads(l) for l in path.read_text().strip().splitlines()]
    assert lines[0]["inputs_digest"] == lines[1]["inputs_digest"]


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root bypasses file permissions, so the unwritable-dir precondition "
    "cannot be established (chmod 0500 does not stop root from writing)",
)
def test_fails_loud_on_unwritable_dir(tmp_path, monkeypatch):
    unwritable = tmp_path / "locked"
    unwritable.mkdir()
    os.chmod(unwritable, stat.S_IREAD | stat.S_IEXEC)  # read+exec only, no write
    monkeypatch.setenv("ONELIVE_REPLAY_LOG_DIR", str(unwritable / "nested"))

    try:
        with pytest.raises(ReplayLogWriteError):
            log_step(_record(new_run_id()))
    finally:
        os.chmod(unwritable, stat.S_IRWXU)  # restore so tmp_path cleanup can remove it


def test_default_log_dir_used_when_env_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("ONELIVE_REPLAY_LOG_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    run_id = new_run_id()
    log_step(_record(run_id))
    assert (tmp_path / "var" / "replay" / f"{run_id}.jsonl").exists()
