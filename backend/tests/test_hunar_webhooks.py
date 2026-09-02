import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.database import get_db
from app.main import app
from app.models import Call, WebhookEvent
from app.routers import webhooks
from app.services.hunar_webhooks import verify_hunar_signature

SECRET = "test-hunar-secret"


def signature(raw_body: bytes, timestamp: str, secret: str = SECRET) -> str:
    digest = hmac.new(
        secret.encode(), timestamp.encode() + b"." + raw_body, hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode()


class FakeWebhookSession:
    def __init__(self, call: Call) -> None:
        self.call = call
        self.events: list[WebhookEvent] = []
        self.pending: list[WebhookEvent] = []
        self.commit_count = 0

    def scalar(self, statement):
        entity = statement.column_descriptions[0].get("entity")
        if entity is WebhookEvent:
            return self.events[0] if self.events else None
        if entity is Call:
            return self.call
        return None

    def add(self, event: WebhookEvent) -> None:
        self.pending.append(event)

    def commit(self) -> None:
        self.commit_count += 1
        for event in self.pending:
            event.id = uuid.uuid4()
            event.created_at = datetime.now(UTC)
            self.events.append(event)
        self.pending.clear()

    def rollback(self) -> None:
        self.pending.clear()


def make_call() -> Call:
    call = Call(
        job_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        hunar_call_id="hunar-call-1",
        request_id="request-1",
        status="QUEUED",
    )
    call.id = uuid.uuid4()
    call.created_at = datetime.now(UTC)
    call.updated_at = datetime.now(UTC)
    return call


def override_database(fake_db: FakeWebhookSession):
    def dependency():
        yield fake_db

    return dependency


def post_signed(client: TestClient, path: str, payload: dict, timestamp: str | None = None):
    raw_body = json.dumps(payload, indent=1).encode()
    signed_at = timestamp or str(int(time.time()))
    return client.post(
        path,
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Hunar-Timestamp": signed_at,
            "X-Hunar-Signature": signature(raw_body, signed_at),
        },
    )


@pytest.fixture
def configured_webhooks(monkeypatch):
    monkeypatch.setattr(
        webhooks,
        "get_settings",
        lambda: SimpleNamespace(hunar_api_key=SecretStr(SECRET)),
    )


def test_signature_verification_uses_raw_bytes_and_constant_digest_format() -> None:
    raw_body = b'{ "request_id": "request-1", "status": "COMPLETED" }'
    timestamp = "1700000000"
    valid_signature = signature(raw_body, timestamp)

    assert verify_hunar_signature(
        raw_body, timestamp, valid_signature, SECRET, now=1700000100
    )
    assert not verify_hunar_signature(
        raw_body + b"\n", timestamp, valid_signature, SECRET, now=1700000100
    )
    assert not verify_hunar_signature(
        raw_body, timestamp, "not-the-signature", SECRET, now=1700000100
    )
    assert not verify_hunar_signature(
        raw_body, timestamp, valid_signature, SECRET, now=1700000301
    )


@pytest.mark.parametrize(
    ("endpoint", "expected_field", "expected_value"),
    [
        ("status", "status", "COMPLETED"),
        ("recording", "recording_url", "https://recordings.example.com/1.mp3"),
        ("result", "result", {"recommended": True}),
        ("summary", "summary", "Strong Python background."),
    ],
)
def test_each_webhook_stores_payload_and_updates_only_relevant_field(
    configured_webhooks,
    endpoint: str,
    expected_field: str,
    expected_value,
) -> None:
    call = make_call()
    fake_db = FakeWebhookSession(call)
    payload = {
        "event_id": f"event-{endpoint}",
        "request_id": call.request_id,
        "call_id": call.hunar_call_id,
        "status": "COMPLETED",
        "recording_url": "https://recordings.example.com/1.mp3",
        "result": {"recommended": True},
        "summary": "Strong Python background.",
    }
    original_values = {
        "status": call.status,
        "recording_url": call.recording_url,
        "result": call.result,
        "summary": call.summary,
    }
    app.dependency_overrides[get_db] = override_database(fake_db)
    try:
        with TestClient(app) as client:
            response = post_signed(client, f"/webhooks/hunar/{endpoint}", payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert fake_db.events[0].payload == payload
    assert fake_db.events[0].event_type == endpoint
    assert getattr(call, expected_field) == expected_value
    for field, original_value in original_values.items():
        if field != expected_field:
            assert getattr(call, field) == original_value


def test_duplicate_webhook_is_acknowledged_without_processing_twice(
    configured_webhooks,
) -> None:
    call = make_call()
    fake_db = FakeWebhookSession(call)
    payload = {
        "event_id": "event-duplicate",
        "request_id": call.request_id,
        "status": "COMPLETED",
    }
    app.dependency_overrides[get_db] = override_database(fake_db)
    try:
        with TestClient(app) as client:
            first = post_signed(client, "/webhooks/hunar/status", payload)
            second = post_signed(client, "/webhooks/hunar/status", payload)
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == second.status_code == 200
    assert len(fake_db.events) == 1
    assert fake_db.commit_count == 1
    assert call.status == "COMPLETED"


def test_invalid_and_expired_signatures_are_rejected(configured_webhooks) -> None:
    fake_db = FakeWebhookSession(make_call())
    app.dependency_overrides[get_db] = override_database(fake_db)
    try:
        with TestClient(app) as client:
            invalid = client.post(
                "/webhooks/hunar/status",
                content=b"{}",
                headers={
                    "Content-Type": "application/json",
                    "X-Hunar-Timestamp": str(int(time.time())),
                    "X-Hunar-Signature": "invalid",
                },
            )
            expired = post_signed(
                client,
                "/webhooks/hunar/status",
                {"event_id": "expired"},
                timestamp=str(int(time.time()) - 301),
            )
    finally:
        app.dependency_overrides.clear()

    assert invalid.status_code == 401
    assert expired.status_code == 401
    assert fake_db.events == []
