import base64
import hashlib
import hmac
import time
from collections.abc import Iterator
from typing import Any


WEBHOOK_MAX_AGE_SECONDS = 300


def verify_hunar_signature(
    raw_body: bytes,
    timestamp: str | None,
    signature: str | None,
    secret: str,
    *,
    now: float | None = None,
) -> bool:
    if not timestamp or not signature or not secret:
        return False
    try:
        timestamp_seconds = float(timestamp)
    except ValueError:
        return False

    current_time = time.time() if now is None else now
    if abs(current_time - timestamp_seconds) > WEBHOOK_MAX_AGE_SECONDS:
        return False

    signing_input = timestamp.encode("utf-8") + b"." + raw_body
    expected_signature = base64.b64encode(
        hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    ).decode("ascii")
    return hmac.compare_digest(expected_signature, signature)


def webhook_event_id(event_type: str, payload: dict[str, Any], raw_body: bytes) -> str:
    for container in iter_payload_containers(payload):
        for key in ("event_id", "webhook_event_id"):
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    digest = hashlib.sha256(event_type.encode("utf-8") + b"." + raw_body).hexdigest()
    return f"payload:{digest}"


def extract_call_identifiers(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    containers = list(iter_payload_containers(payload))
    request_id = first_string(containers, ("request_id", "requestId"))
    hunar_call_id = first_string(
        containers,
        ("hunar_call_id", "call_id", "callId"),
    )
    if hunar_call_id is None:
        call_payload = nested_call_payload(payload)
        if call_payload is not None:
            hunar_call_id = string_value(call_payload.get("id"))
    return request_id, hunar_call_id


def relevant_webhook_value(payload: dict[str, Any], *keys: str) -> Any:
    for container in iter_payload_containers(payload):
        for key in keys:
            if key in container:
                return container[key]
    return None


def iter_payload_containers(payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield payload
    data = payload.get("data")
    if isinstance(data, dict):
        yield data
        call = data.get("call")
        if isinstance(call, dict):
            yield call
    call = payload.get("call")
    if isinstance(call, dict):
        yield call


def nested_call_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    call = payload.get("call")
    if isinstance(call, dict):
        return call
    data = payload.get("data")
    if isinstance(data, dict):
        call = data.get("call")
        if isinstance(call, dict):
            return call
        return data
    return None


def first_string(containers: list[dict[str, Any]], keys: tuple[str, ...]) -> str | None:
    for container in containers:
        for key in keys:
            value = string_value(container.get(key))
            if value is not None:
                return value
    return None


def string_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
