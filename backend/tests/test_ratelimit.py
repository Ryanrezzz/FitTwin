"""The auth rate limiter — brute-force protection, verified rather than assumed."""
import pytest

from app.config import settings
from app.core import ratelimit


@pytest.fixture()
def limited():
    """Turn the limiter on for this test only (the suite disables it globally)."""
    ratelimit.reset()
    settings.rate_limit_enabled = True
    yield
    settings.rate_limit_enabled = False
    ratelimit.reset()


def test_login_blocks_brute_force(client, limited):
    """Wrong passwords must stop being answered, not answered forever."""
    body = {"email": "nobody@example.com", "password": "wrong-password"}
    codes = [client.post("/api/v1/auth/login", json=body).status_code for _ in range(12)]
    assert 429 in codes, "login accepted unlimited attempts"
    assert codes.index(429) <= 9, "limiter kicked in too late"


def test_limit_response_tells_the_user_when_to_retry(client, limited):
    body = {"email": "nobody@example.com", "password": "wrong-password"}
    last = None
    for _ in range(12):
        last = client.post("/api/v1/auth/login", json=body)
    assert last.status_code == 429
    assert int(last.headers["Retry-After"]) > 0


def test_disabled_limiter_is_a_no_op(client):
    """With the flag off nothing throttles — this is what the suite relies on."""
    body = {"email": "nobody@example.com", "password": "wrong-password"}
    codes = {client.post("/api/v1/auth/login", json=body).status_code for _ in range(15)}
    assert codes == {401}
