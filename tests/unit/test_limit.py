import pytest
from mybot.limiter import limit_user, UsageLimitExceeded

def test_limit_increment(redis_client):
    for _ in range(5):
        ok = limit_user("123")
    assert ok is True

def test_limit_exceeded(redis_client):
    for _ in range(5):
        limit_user("999")
    with pytest.raises(UsageLimitExceeded):
        limit_user("999") 