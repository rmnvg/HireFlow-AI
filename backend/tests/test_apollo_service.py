import json
import uuid

import httpx
import pytest

from app.services.apollo import (
    ApolloAuthenticationError,
    ApolloContactService,
    ApolloPermissionError,
    ApolloRateLimitError,
    ApolloTimeoutError,
    normalize_apollo_contact,
)

APOLLO_URL = "https://api.apollo.io/api/v1/contacts/search"
TEST_KEY = "test-apollo-key"


def make_service(handler) -> tuple[ApolloContactService, httpx.Client]:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    timeout = httpx.Timeout(5.0, connect=2.0)
    return (
        ApolloContactService(
            client=client,
            api_key=TEST_KEY,
            contacts_url=APOLLO_URL,
            timeout=timeout,
        ),
        client,
    )


def test_keyword_search_uses_expected_headers_and_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Api-Key"] == TEST_KEY
        assert request.headers["Content-Type"] == "application/json"
        assert json.loads(request.content) == {
            "q_keywords": "Python FastAPI",
            "page": 1,
            "per_page": 10,
        }
        return httpx.Response(200, json={"contacts": [{"id": "apollo-1", "name": "Aisha"}]})

    service, client = make_service(handler)
    try:
        result = service.search_contacts("Python FastAPI")
    finally:
        client.close()

    assert result.fallback_without_keywords is False
    assert result.contacts[0]["id"] == "apollo-1"


def test_empty_keyword_result_retries_once_without_keywords() -> None:
    payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(json.loads(request.content))
        contacts = [] if len(payloads) == 1 else [{"id": "apollo-2", "name": "Rohan"}]
        return httpx.Response(200, json={"contacts": contacts})

    service, client = make_service(handler)
    try:
        result = service.search_contacts("Backend Engineer")
    finally:
        client.close()

    assert payloads == [
        {"q_keywords": "Backend Engineer", "page": 1, "per_page": 10},
        {"page": 1, "per_page": 10},
    ]
    assert result.fallback_without_keywords is True
    assert result.contacts[0]["id"] == "apollo-2"


@pytest.mark.parametrize(
    ("status_code", "expected_exception"),
    [
        (401, ApolloAuthenticationError),
        (403, ApolloPermissionError),
        (429, ApolloRateLimitError),
    ],
)
def test_apollo_status_errors_are_mapped(status_code, expected_exception) -> None:
    service, client = make_service(
        lambda _: httpx.Response(status_code, text="response details must remain private")
    )
    try:
        with pytest.raises(expected_exception):
            service.search_contacts("Python")
    finally:
        client.close()


def test_apollo_timeout_is_mapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("request headers", request=request)

    service, client = make_service(handler)
    try:
        with pytest.raises(ApolloTimeoutError):
            service.search_contacts("Python")
    finally:
        client.close()


def test_apollo_contact_is_normalized_without_losing_raw_profile() -> None:
    job_id = uuid.uuid4()
    raw_contact = {
        "id": "apollo-3",
        "first_name": "Nina",
        "last_name": "Shah",
        "title": "Backend Engineer",
        "organization": {"name": "Example Labs"},
        "city": "Mumbai",
        "country": "India",
        "email": "nina@example.com",
        "phone_numbers": [{"sanitized_number": "+919999999999"}],
    }

    normalized = normalize_apollo_contact(raw_contact, job_id)

    assert normalized is not None
    assert normalized["name"] == "Nina Shah"
    assert normalized["company"] == "Example Labs"
    assert normalized["location"] == "Mumbai, India"
    assert normalized["phone"] == "+919999999999"
    assert normalized["raw_profile"] is raw_contact
