import pytest
from datetime import datetime, timedelta
from backend.utils import parse_expiry_string

@pytest.mark.unit
def test_parse_expiry_string_minutes():
    expires_at = parse_expiry_string("10m")
    assert expires_at is not None
    # Check if it's roughly 10 minutes from now (allowing for slight execution time)
    diff = expires_at - datetime.utcnow()
    assert 590 <= diff.total_seconds() <= 610  # 10 min +/- 10s

@pytest.mark.unit
def test_parse_expiry_string_hours():
    expires_at = parse_expiry_string("1h")
    assert expires_at is not None
    diff = expires_at - datetime.utcnow()
    assert 3590 <= diff.total_seconds() <= 3610

@pytest.mark.unit
def test_parse_expiry_string_days():
    expires_at = parse_expiry_string("2d")
    assert expires_at is not None
    diff = expires_at - datetime.utcnow()
    assert 172790 <= diff.total_seconds() <= 172810  # 2 days +/- 10s

@pytest.mark.unit
def test_parse_expiry_string_weeks():
    expires_at = parse_expiry_string("1w")
    assert expires_at is not None
    diff = expires_at - datetime.utcnow()
    assert 604790 <= diff.total_seconds() <= 604810  # 1 week +/- 10s

@pytest.mark.unit
def test_parse_expiry_string_months():
    expires_at = parse_expiry_string("1M")
    assert expires_at is not None
    diff = expires_at - datetime.utcnow()
    assert 2591990 <= diff.total_seconds() <= 2592010  # 30 days +/- 10s

@pytest.mark.unit
def test_parse_expiry_string_years():
    expires_at = parse_expiry_string("1y")
    assert expires_at is not None
    diff = expires_at - datetime.utcnow()
    assert 31535990 <= diff.total_seconds() <= 31536010  # 365 days +/- 10s

@pytest.mark.unit
def test_parse_expiry_string_never():
    assert parse_expiry_string("never") is None
    assert parse_expiry_string(None) is None
    assert parse_expiry_string("") is None

@pytest.mark.unit
def test_parse_expiry_string_invalid():
    assert parse_expiry_string("invalid") is None
    assert parse_expiry_string("10x") is None
    assert parse_expiry_string("abc") is None
