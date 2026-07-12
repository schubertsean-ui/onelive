"""Tests for the input-quality/context-hygiene sensor (worker/sensors.py).

Pure-logic, hermetic: no network, no DB.
"""
from worker.sensors import MIN_TEXT_LENGTH, assess_input


def test_rejects_none_text():
    reading = assess_input(text=None, content_type="text/html")
    assert reading.ok is False
    assert "none" in reading.reason.lower()


def test_rejects_empty_text():
    reading = assess_input(text="", content_type="text/html")
    assert reading.ok is False
    assert "empty" in reading.reason.lower()


def test_rejects_whitespace_only_text():
    reading = assess_input(text="   \n\t  ", content_type="text/html")
    assert reading.ok is False
    assert "empty" in reading.reason.lower()


def test_rejects_too_short_text():
    reading = assess_input(text="short", content_type="text/html")
    assert reading.ok is False
    assert "too short" in reading.reason.lower()


def test_accepts_text_at_minimum_length_boundary():
    text = "x" * MIN_TEXT_LENGTH
    reading = assess_input(text=text, content_type="text/plain")
    assert reading.ok is True


def test_rejects_binary_content_type():
    text = "A" * 100
    reading = assess_input(text=text, content_type="image/png")
    assert reading.ok is False
    assert "binary" in reading.reason.lower()


def test_rejects_binary_looking_payload():
    # Embedded NUL bytes are impossible in valid text.
    text = "\x00\x01\x02" * 30
    reading = assess_input(text=text, content_type="text/plain")
    assert reading.ok is False


def test_rejects_known_error_page():
    text = "Sorry, this page isn't working. " * 3
    reading = assess_input(text=text, content_type="text/html")
    assert reading.ok is False
    assert "error/placeholder" in reading.reason.lower()


def test_rejects_404_page():
    text = "404 Not Found - the page you requested does not exist on this server."
    reading = assess_input(text=text, content_type="text/html")
    assert reading.ok is False


def test_accepts_real_listing_blurb():
    text = (
        "TONIGHT @ Mohawk Austin\n"
        "Doors 7pm / Show 8pm\n"
        "Artist: Example Band with special guests\n"
        "Tickets: https://example.com/tickets\n"
    )
    reading = assess_input(text=text, content_type="text/html; charset=utf-8")
    assert reading.ok is True
    assert reading.signals["stripped_length"] == len(text.strip())


def test_signals_present_on_both_ok_and_rejected():
    ok_reading = assess_input(text="A" * 100, content_type="text/plain")
    bad_reading = assess_input(text="", content_type="text/plain")
    assert "raw_length" in ok_reading.signals
    assert "raw_length" in bad_reading.signals
