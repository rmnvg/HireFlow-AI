import uuid
from dataclasses import dataclass
from typing import Any

import httpx


class ApolloServiceError(Exception):
    """Base exception for safe Apollo failure handling."""


class ApolloAuthenticationError(ApolloServiceError):
    pass


class ApolloPermissionError(ApolloServiceError):
    pass


class ApolloRateLimitError(ApolloServiceError):
    pass


class ApolloTimeoutError(ApolloServiceError):
    pass


class ApolloUnavailableError(ApolloServiceError):
    pass


@dataclass(frozen=True)
class ApolloSearchResult:
    contacts: list[dict[str, Any]]
    fallback_without_keywords: bool


class ApolloContactService:
    def __init__(
        self,
        client: httpx.Client,
        api_key: str,
        contacts_url: str,
        timeout: httpx.Timeout,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._contacts_url = contacts_url
        self._timeout = timeout

    def search_contacts(self, search_keywords: str) -> ApolloSearchResult:
        keywords = search_keywords.strip()
        if not keywords:
            return ApolloSearchResult(
                contacts=self._request_contacts(q_keywords=None),
                fallback_without_keywords=True,
            )

        contacts = self._request_contacts(q_keywords=keywords)
        if contacts:
            return ApolloSearchResult(contacts=contacts, fallback_without_keywords=False)

        return ApolloSearchResult(
            contacts=self._request_contacts(q_keywords=None),
            fallback_without_keywords=True,
        )

    def _request_contacts(self, q_keywords: str | None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"page": 1, "per_page": 10}
        if q_keywords is not None:
            payload["q_keywords"] = q_keywords

        try:
            response = self._client.post(
                self._contacts_url,
                headers={
                    "X-Api-Key": self._api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise ApolloTimeoutError("Apollo request timed out") from exc
        except httpx.RequestError as exc:
            raise ApolloUnavailableError("Apollo request failed") from exc

        if response.status_code == 401:
            raise ApolloAuthenticationError("Apollo rejected the API key")
        if response.status_code == 403:
            raise ApolloPermissionError("Apollo contact search is forbidden")
        if response.status_code == 429:
            raise ApolloRateLimitError("Apollo rate limit reached")
        if response.is_error:
            raise ApolloUnavailableError("Apollo returned an unexpected error")

        try:
            payload_data = response.json()
        except ValueError as exc:
            raise ApolloUnavailableError("Apollo returned invalid JSON") from exc

        contacts = payload_data.get("contacts") if isinstance(payload_data, dict) else None
        if not isinstance(contacts, list):
            raise ApolloUnavailableError("Apollo response did not include contacts")
        return [contact for contact in contacts if isinstance(contact, dict)]


def normalize_apollo_contact(
    contact: dict[str, Any], job_id: uuid.UUID
) -> dict[str, Any] | None:
    apollo_id = contact.get("id")
    name = contact.get("name")
    if not isinstance(name, str) or not name.strip():
        name_parts = [contact.get("first_name"), contact.get("last_name")]
        name = " ".join(
            part.strip() for part in name_parts if isinstance(part, str) and part.strip()
        )

    if not isinstance(apollo_id, str) or not apollo_id.strip() or not name:
        return None

    def optional_string(value: Any) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

    organization = contact.get("organization")
    organization_name = contact.get("organization_name")
    if not organization_name and isinstance(organization, dict):
        organization_name = organization.get("name")
    organization_name = optional_string(organization_name)

    location = contact.get("present_raw_address")
    if not location:
        location_parts = [contact.get("city"), contact.get("state"), contact.get("country")]
        location = ", ".join(
            part.strip() for part in location_parts if isinstance(part, str) and part.strip()
        )
    if not location:
        location = None

    phone = None
    phone_numbers = contact.get("phone_numbers")
    if isinstance(phone_numbers, list):
        for phone_entry in phone_numbers:
            if not isinstance(phone_entry, dict):
                continue
            phone = (
                phone_entry.get("sanitized_number")
                or phone_entry.get("raw_number")
                or phone_entry.get("number")
            )
            if isinstance(phone, str) and phone.strip():
                break
            phone = None

    return {
        "job_id": job_id,
        "apollo_id": apollo_id.strip(),
        "name": name.strip(),
        "current_title": optional_string(contact.get("title")),
        "company": organization_name,
        "location": location,
        "email": optional_string(contact.get("email")),
        "phone": phone,
        "source": "apollo",
        "raw_profile": contact,
    }
