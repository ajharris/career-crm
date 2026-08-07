"""Provider plugin, encrypted credential, and optional-profile regression tests."""

from cryptography.fernet import Fernet

from app.ai.services import (
    AIProvider,
    CredentialService,
    DeterministicProvider,
    ProviderConfig,
    ProviderRegistry,
    provider_for_user,
)
from app.extensions import db
from app.models import CareerProfile, UserAIProviderCredential


class ExampleProvider(AIProvider):
    key = "example"
    label = "Example"
    requires_credential = False

    def generate(self, task: str, context: dict) -> str:
        return f"example:{task}:{context.get('title')}"


def test_registry_accepts_new_provider_without_route_changes():
    registry = ProviderRegistry()
    registry.register(ExampleProvider)
    provider = registry.create("example", ProviderConfig(model="local"))
    assert provider.generate("job_summary", {"title": "Engineer"}) == (
        "example:job_summary:Engineer"
    )
    assert registry.choices() == [("example", "Example")]


def test_deterministic_provider_needs_no_key_or_network():
    provider = DeterministicProvider(ProviderConfig())
    result = provider.generate("job_summary", {"job": "Engineer"})
    assert "Engineer" in result


def test_credentials_are_encrypted_replaced_and_disconnected(app, user):
    app.config["CREDENTIAL_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    first = CredentialService.save(user.id, "openai", "sk-first-secret")
    assert "sk-first-secret" not in first.encrypted_secret
    assert CredentialService.decrypt(first) == "sk-first-secret"
    first_id = first.id

    replaced = CredentialService.save(user.id, "openai", "sk-replacement")
    assert replaced.id == first_id
    assert CredentialService.decrypt(replaced) == "sk-replacement"
    assert db.session.scalar(db.select(db.func.count(UserAIProviderCredential.id))) == 1

    CredentialService.disconnect(user.id, "openai")
    assert db.session.get(UserAIProviderCredential, first_id) is None


def test_user_provider_uses_profile_selection_and_own_credential(app, user):
    app.config["CREDENTIAL_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    profile = db.session.scalar(
        db.select(CareerProfile).where(CareerProfile.user_id == user.id)
    )
    profile.preferred_ai_provider = "openai"
    profile.preferred_ai_model = "custom-model"
    db.session.commit()
    CredentialService.save(user.id, "openai", "sk-user-owned")

    provider = provider_for_user(user.id)
    assert provider.config.api_key == "sk-user-owned"
    assert provider.config.model == "custom-model"


def test_ai_settings_never_render_plaintext_key(authenticated_client, app):
    app.config["CREDENTIAL_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    response = authenticated_client.post(
        "/assistant/settings",
        data={
            "provider": "openai",
            "model": "gpt-test",
            "api_key": "sk-never-render-this",
            "enabled": "y",
            "action": "save",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"sk-never-render-this" not in response.data
    assert b"AI settings saved" in response.data


def test_new_user_dashboard_is_available_without_onboarding(client):
    response = client.post(
        "/auth/register",
        data={
            "first_name": "Optional",
            "last_name": "Profile",
            "email": "optional@example.com",
            "password": "correct horse battery staple",
            "confirm_password": "correct horse battery staple",
        },
    )
    assert response.location == "/"
    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert b"Complete Your Career Profile" in dashboard.data
