"""Tests for tools/assemble_dsn.py — as-pasted DSN + separate password.

Proves: passthrough of a fully-edited DSN; placeholder splice with URL
encoding of reserved characters; fail-closed on placeholder-without-
password, empty DSN, and line breaks; stdout carries ONLY the DSN; error
output never contains secret material (evaluator findings, PR #19 r1).
"""
import importlib.util
import pathlib
import sys

import pytest

_TOOL_PATH = pathlib.Path(__file__).resolve().parent.parent / "tools" / "assemble_dsn.py"
_spec = importlib.util.spec_from_file_location("assemble_dsn", _TOOL_PATH)
ad = importlib.util.module_from_spec(_spec)
sys.modules["assemble_dsn"] = ad
_spec.loader.exec_module(ad)

RAW = "postgresql://postgres.ref:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres"


def test_passthrough_when_no_placeholder():
    assert ad.assemble("postgresql://u:realpw@h:5432/db", "") == "postgresql://u:realpw@h:5432/db"


def test_splice_url_encodes_reserved_characters():
    out = ad.assemble(RAW, "p@ss:w/r%d")
    assert "[YOUR-PASSWORD]" not in out
    assert "p%40ss%3Aw%2Fr%25d" in out


def test_placeholder_without_password_fails_closed():
    with pytest.raises(ValueError, match="ONELIVE_DB_PASSWORD"):
        ad.assemble(RAW, "")
    with pytest.raises(ValueError):
        ad.assemble(RAW, "   ")


def test_empty_dsn_fails_closed():
    with pytest.raises(ValueError, match="empty"):
        ad.assemble("", "pw")


def test_interior_line_breaks_rejected():
    with pytest.raises(ValueError, match="line break"):
        ad.assemble("postgresql://u:pw@h:5432\n/db", "")
    with pytest.raises(ValueError, match="line break"):
        ad.assemble("postgresql://u:pw@h\r:5432/db", "")


def test_cli_stdout_is_exactly_the_dsn_and_nothing_else(monkeypatch, capsys):
    monkeypatch.setenv("ONELIVE_DB_DSN_RAW", RAW)
    monkeypatch.setenv("ONELIVE_DB_PASSWORD", "secret-pw")
    assert ad.main([]) == 0
    captured = capsys.readouterr()
    assert captured.out == ad.assemble(RAW, "secret-pw") + "\n"
    assert captured.err == ""


def test_outer_whitespace_is_normalized_not_fatal():
    """Trailing newline/space is the most common paste artifact — strip it
    rather than punish the paste; interior whitespace still hard-fails."""
    assert ad.assemble("  " + RAW.replace("[YOUR-PASSWORD]", "pw") + "\n", "") == \
        RAW.replace("[YOUR-PASSWORD]", "pw")
    with pytest.raises(ValueError, match="interior"):
        ad.assemble("postgresql://u:p w@h/db", "")


def test_mask_command_output_is_workflow_escaped(monkeypatch, capsys):
    """The registered mask must equal the true DSN after the runner
    unescapes it — '%' sequences from URL encoding are the leak case
    (evaluator, PR #19 rounds 1-2)."""
    monkeypatch.setenv("ONELIVE_DB_DSN_RAW", RAW)
    monkeypatch.setenv("ONELIVE_DB_PASSWORD", "p@ss%1")
    assert ad.main(["--mask-command"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("::add-mask::")
    # true DSN contains p%40ss%251; the command must carry p%2540ss%25251
    assert "p%2540ss%25251" in out
    assert "p%40ss%251" not in out.replace("p%2540ss%25251", "")


def test_escape_order_percent_first():
    assert ad.escape_workflow_command_value("%0A\n") == "%250A%0A"


def test_cli_error_output_contains_no_secret_material(monkeypatch, capsys):
    """Misconfig messages may land in CI logs — they must never echo the
    DSN or password values themselves."""
    monkeypatch.setenv("ONELIVE_DB_DSN_RAW", RAW)
    monkeypatch.setenv("ONELIVE_DB_PASSWORD", "")
    assert ad.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "pooler.supabase.com" not in captured.err  # no DSN fragments
    assert "postgres" not in captured.err


def test_error_paths_with_secrets_present_leak_nothing(monkeypatch, capsys):
    """Lock the no-secret-in-errors invariant on a path where secret
    material EXISTS (evaluator nit, PR #19 round 2): interior-whitespace
    DSN + a real password."""
    monkeypatch.setenv("ONELIVE_DB_DSN_RAW",
                       "postgresql://u:[YOUR-PASSWORD]@h h/db")
    monkeypatch.setenv("ONELIVE_DB_PASSWORD", "hunter2secret")
    assert ad.main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "hunter2secret" not in captured.err
    assert "postgresql" not in captured.err
