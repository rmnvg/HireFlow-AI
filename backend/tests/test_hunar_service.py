import json

import httpx
import pytest

from app.services.hunar import (
    HunarAuthenticationError,
    HunarFieldError,
    HunarNotFoundError,
    HunarProviderError,
    HunarRateLimitError,
    HunarSubscriptionError,
    HunarTimeoutError,
    HunarValidationError,
    HunarVoiceService,
    extract_required_agent_variables,
    get_hunar_call_id,
)

HUNAR_BASE_URL = "https://api.voice.hunar.ai/external/v1"
TEST_KEY = "test-hunar-key"


def make_service(handler) -> tuple[HunarVoiceService, httpx.Client]:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    timeout = httpx.Timeout(5.0, connect=2.0)
    return (
        HunarVoiceService(
            client=client,
            api_key=TEST_KEY,
            base_url=HUNAR_BASE_URL,
            timeout=timeout,
        ),
        client,
    )


def test_hunar_client_uses_expected_paths_header_and_call_payload() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["X-API-Key"] == TEST_KEY
        if request.url.path.endswith("/agents/"):
            return httpx.Response(200, json={"agents": [{"id": "agent-1"}]})
        if request.url.path.endswith("/agents/agent-1/"):
            return httpx.Response(200, json={"id": "agent-1"})
        if request.method == "POST":
            assert json.loads(request.content)["mobile_number"] == "+919876543210"
            return httpx.Response(201, json={"id": "call-1", "status": "QUEUED"})
        return httpx.Response(200, json={"id": "call-1", "status": "COMPLETED"})

    service, client = make_service(handler)
    try:
        assert service.list_agents()["agents"][0]["id"] == "agent-1"
        assert service.get_agent("agent-1")["id"] == "agent-1"
        created = service.create_call({"mobile_number": "+919876543210"})
        refreshed = service.get_call("call-1")
    finally:
        client.close()

    assert created["status"] == "QUEUED"
    assert refreshed["status"] == "COMPLETED"
    assert [request.url.path for request in requests] == [
        "/external/v1/agents/",
        "/external/v1/agents/agent-1/",
        "/external/v1/calls/",
        "/external/v1/calls/call-1/",
    ]


@pytest.mark.parametrize(
    ("status_code", "exception_type"),
    [
        (400, HunarValidationError),
        (401, HunarAuthenticationError),
        (402, HunarSubscriptionError),
        (404, HunarNotFoundError),
        (422, HunarFieldError),
        (429, HunarRateLimitError),
        (500, HunarProviderError),
        (503, HunarProviderError),
    ],
)
def test_hunar_http_errors_are_mapped(status_code, exception_type) -> None:
    service, client = make_service(
        lambda _: httpx.Response(status_code, text="private provider response")
    )
    try:
        with pytest.raises(exception_type):
            service.list_agents()
    finally:
        client.close()


def test_hunar_timeout_is_mapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("phone and headers", request=request)

    service, client = make_service(handler)
    try:
        with pytest.raises(HunarTimeoutError):
            service.list_agents()
    finally:
        client.close()


def test_required_agent_variables_support_common_metadata_shapes() -> None:
    agent = {
        "data": {
            "agent": {
                "required_variables": ["job_role", {"name": "company"}],
                "variables": [
                    {"name": "location", "required": True},
                    {"name": "optional_note", "required": False},
                ],
                "custom_data_variables": {
                    "candidate_language": {"required": True},
                },
            }
        }
    }

    assert extract_required_agent_variables(agent) == [
        "job_role",
        "company",
        "location",
        "candidate_language",
    ]


def test_hunar_call_id_supports_nested_response() -> None:
    assert get_hunar_call_id({"data": {"call": {"call_id": "hunar-call-1"}}}) == "hunar-call-1"
