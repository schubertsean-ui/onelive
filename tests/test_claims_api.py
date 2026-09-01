"""The claim API's DB branches — every one of them, against a fake cursor.

HERMETIC: no Postgres. The point is not to test psycopg2 but to prove the
BRANCH LOGIC the evaluator found missing (PR #203, untested-gate-branch): what
happens when the `source` upsert's fence declines the update because the venue
name already belongs to something a claim does not own.

That fence is the difference between "a claim registers a venue" and "untrusted
input silently disables a trusted source", so it ships with a test per branch.
"""
import json

import pytest
from fastapi import HTTPException

from api.claims import ClaimIn, record_claim
from worker.claim.intake import FORWARD_ADDRESS_ENV


class FakeCursor:
    """Returns programmed results per execute, and records the SQL it saw."""

    def __init__(self, upsert_row, existing_rows):
        self._upsert_row = upsert_row
        self._existing_rows = existing_rows
        self._last = ""
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self._last = sql
        self.executed.append((sql, params))

    def fetchone(self):
        return self._upsert_row

    def fetchall(self):
        return self._existing_rows


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


ADMIN = {"email": "ops@onelive.test"}


def _payload(**over):
    base = dict(venue_name="Mohawk Austin", submitter_role="organizer",
                intake_mode="email_forward")
    base.update(over)
    return ClaimIn(**base)


@pytest.fixture(autouse=True)
def _mailbox(monkeypatch):
    # The email-forward lane fails closed without a configured mailbox; these
    # tests are about the SOURCE branch, so give it one.
    monkeypatch.setenv(FORWARD_ADDRESS_ENV, "listings@example.test")


def test_a_fresh_claim_records_the_source_and_commits():
    cur = FakeCursor(upsert_row=("11111111-1111-1111-1111-111111111111",), existing_rows=[])
    conn = FakeConn(cur)
    receipt = record_claim(_payload(), admin=ADMIN, conn=conn)

    assert receipt["source_id"] == "11111111-1111-1111-1111-111111111111"
    assert receipt["confidence"] == "unverified"
    assert receipt["enabled"] is False
    assert receipt["status"] == ["received", "held", "not live"]
    assert conn.committed is True


def test_the_upsert_is_fenced_to_claim_owned_source_types():
    """The guard must be IN THE SQL, not merely intended: the conflict key is
    the venue name and the venue name comes from the submitter."""
    cur = FakeCursor(upsert_row=("11111111-1111-1111-1111-111111111111",), existing_rows=[])
    record_claim(_payload(), admin=ADMIN, conn=FakeConn(cur))

    sql, params = cur.executed[0]
    assert "on conflict" in sql.lower()
    assert "where source.source_type = any(" in sql.lower()
    assert params[-1] == ["claimed_upload_unverified", "human_report"]


def test_a_name_collision_with_a_non_claim_source_refuses_and_records_nothing():
    """The blocker this fence exists for: without it, recording a claim for a
    name an existing TRUSTED source holds would overwrite that source's
    metadata and flip it enabled=false — untrusted input causing real catalog
    coverage loss."""
    cur = FakeCursor(
        upsert_row=None,
        existing_rows=[("22222222-2222-2222-2222-222222222222", "venue_calendar", True)],
    )
    conn = FakeConn(cur)
    with pytest.raises(HTTPException) as excinfo:
        record_claim(_payload(), admin=ADMIN, conn=conn)

    assert excinfo.value.status_code == 409
    detail = excinfo.value.detail
    assert "venue_calendar" in detail
    assert "Nothing was recorded" in detail
    assert conn.committed is False
    assert conn.rolled_back is True


def test_a_duplicate_name_means_the_unique_index_is_gone_and_never_guesses():
    cur = FakeCursor(
        upsert_row=None,
        existing_rows=[("2" * 36, "claimed_upload_unverified", False),
                       ("3" * 36, "venue_calendar", True)],
    )
    conn = FakeConn(cur)
    with pytest.raises(HTTPException) as excinfo:
        record_claim(_payload(), admin=ADMIN, conn=conn)

    assert excinfo.value.status_code == 500
    assert "unique index" in excinfo.value.detail
    assert conn.committed is False


def test_no_row_and_no_collision_is_structural_and_fails_loud():
    cur = FakeCursor(upsert_row=None, existing_rows=[])
    conn = FakeConn(cur)
    with pytest.raises(HTTPException) as excinfo:
        record_claim(_payload(), admin=ADMIN, conn=conn)

    assert excinfo.value.status_code == 500
    assert "nothing was recorded" in excinfo.value.detail.lower()
    assert conn.committed is False


def test_a_refused_claim_never_reaches_the_database():
    """Validation runs before any write, so a bad submission cannot get partway
    in — the refusal is a 422 and the cursor was never touched."""
    cur = FakeCursor(upsert_row=("1" * 36,), existing_rows=[])
    conn = FakeConn(cur)
    with pytest.raises(HTTPException) as excinfo:
        record_claim(_payload(intake_mode="ics_url",
                              feed_url="https://example.com/login"),
                     admin=ADMIN, conn=conn)

    assert excinfo.value.status_code == 422
    assert cur.executed == []
    assert conn.committed is False


def test_the_recorder_identity_comes_from_the_session_not_the_request():
    """caller-suppliable-custody-inputs: the claim must not name who recorded it."""
    cur = FakeCursor(upsert_row=("1" * 36,), existing_rows=[])
    record_claim(_payload(), admin={"email": "someone@onelive.test"}, conn=FakeConn(cur))

    _, params = cur.executed[0]
    config = json.loads(params[3])
    assert config["claim"]["recorded_by"] == "someone@onelive.test"
    assert config["claim"]["verified"] is False
    assert config["confidence"] == "unverified"
