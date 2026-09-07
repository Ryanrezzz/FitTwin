"""Google Sign-In — verification, account linking, and the invariants that
keep it from becoming an account-takeover vector.

The token itself is never trusted: `verify_id_token` is the only place a
credential turns into an identity, so these tests stub *that* seam and exercise
everything built on top of it.
"""
import pytest

from app.core.google_oauth import GoogleAuthUnavailable, GoogleIdentity
from app.core.security import AuthError, hash_password
from app.services import auth_service as auth_module
from app.services.auth_service import AuthService
from tests.conftest import InMemoryUserRepo

IDENTITY = GoogleIdentity(
    sub="google-sub-123",
    email="ravi@gmail.com",
    email_verified=True,
    name="Ravi",
    picture="https://example.com/a.jpg",
)


@pytest.fixture()
def users():
    return InMemoryUserRepo()


@pytest.fixture()
def service(users):
    return AuthService(users)


@pytest.fixture()
def google(monkeypatch):
    """Stub the verifier; each test decides what Google 'returned'."""
    def _set(identity=IDENTITY, error=None):
        def fake(credential, **kw):
            if error:
                raise error
            return identity
        monkeypatch.setattr(auth_module, "verify_id_token", fake)
    return _set


# ── account resolution ───────────────────────────────────────────────────────
async def test_first_google_sign_in_creates_a_passwordless_account(service, google):
    google()
    user, created = await service.sign_in_with_google("tok")
    assert created is True
    assert user.email == "ravi@gmail.com"
    assert user.google_sub == "google-sub-123"
    assert user.password_hash is None
    assert user.email_verified is True
    assert user.providers == ["google"]


async def test_second_sign_in_reuses_the_same_account(service, google):
    google()
    first, _ = await service.sign_in_with_google("tok")
    second, created = await service.sign_in_with_google("tok")
    assert created is False
    assert str(second.id) == str(first.id)


async def test_google_links_to_an_existing_password_account(service, users, google):
    """Same verified email -> one account, not a duplicate that loses their data."""
    existing = await users.create(email="ravi@gmail.com", password_hash=hash_password("pw12345678"))
    google()
    user, created = await service.sign_in_with_google("tok")
    assert created is False
    assert str(user.id) == str(existing.id)
    assert user.google_sub == "google-sub-123"
    # Linking is additive: the password must keep working.
    assert user.password_hash is not None
    assert set(user.providers) == {"password", "google"}


async def test_changed_gmail_address_still_finds_the_account_by_sub(service, google):
    """`sub` is the join key precisely so a renamed address doesn't orphan data."""
    google()
    original, _ = await service.sign_in_with_google("tok")
    google(GoogleIdentity(sub="google-sub-123", email="ravi.new@gmail.com", email_verified=True))
    same, created = await service.sign_in_with_google("tok")
    assert created is False
    assert str(same.id) == str(original.id)


# ── security invariants ──────────────────────────────────────────────────────
async def test_a_google_only_account_cannot_be_password_logged_in(service, google):
    """`password_hash = None` must be a rejection, never 'no password needed'."""
    google()
    await service.sign_in_with_google("tok")
    for attempt in ("", " ", "password", "None"):
        with pytest.raises(AuthError):
            await service.authenticate(email="ravi@gmail.com", password=attempt)


async def test_disabled_account_cannot_sign_in_with_google(service, users, google):
    user = await users.create(email="ravi@gmail.com", password_hash=hash_password("pw12345678"))
    user.is_active = False
    await users.save(user)
    google()
    with pytest.raises(AuthError):
        await service.sign_in_with_google("tok")


async def test_invalid_credential_is_rejected(service, google):
    google(error=AuthError("Invalid Google credential"))
    with pytest.raises(AuthError):
        await service.sign_in_with_google("forged")


async def test_unconfigured_server_reports_unavailable_not_broken(service, google):
    google(error=GoogleAuthUnavailable("not configured"))
    with pytest.raises(GoogleAuthUnavailable):
        await service.sign_in_with_google("tok")


# ── HTTP surface ─────────────────────────────────────────────────────────────
@pytest.fixture()
def unconfigured(monkeypatch):
    """Force the feature off regardless of the developer's own .env.

    These assert the *disabled* behaviour, so they must not depend on whether
    whoever runs the suite happens to have a real GOOGLE_CLIENT_ID locally.
    """
    from app.config import settings
    monkeypatch.setattr(settings, "google_client_id", "")


def test_config_endpoint_reports_disabled_when_unset(client, unconfigured):
    body = client.get("/api/v1/auth/google/config").json()
    assert body["enabled"] is False
    assert body["client_id"] == ""


def test_google_endpoint_503s_when_not_configured(client, unconfigured):
    r = client.post("/api/v1/auth/google", json={"credential": "x" * 32})
    assert r.status_code == 503


def test_google_endpoint_validates_its_input(client, unconfigured):
    assert client.post("/api/v1/auth/google", json={}).status_code == 422
    assert client.post("/api/v1/auth/google", json={"credential": "short"}).status_code == 422
    # extra="forbid" — unknown fields are a client bug, not silently ignored
    r = client.post("/api/v1/auth/google", json={"credential": "x" * 32, "role": "admin"})
    assert r.status_code == 422
