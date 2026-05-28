"""Google Contacts (People API) client wrapper.

Handles contact listing, searching, and creation.
Auth is delegated to google_auth.
"""

import logging
from typing import Optional

from usr.plugins.google.helpers.google_auth import (
    get_google_config, build_service, GoogleAuthError,
)

logger = logging.getLogger("google.contacts_client")


class ContactsClient:
    """Google People API wrapper for contacts."""

    last_error: str = ""

    def __init__(self, service):
        self._service = service

    @classmethod
    def from_config(cls, agent=None) -> Optional["ContactsClient"]:
        """Build a ContactsClient from plugin config. Returns None if unavailable."""
        config = get_google_config(agent)
        try:
            service = build_service("contacts", config)
            cls.last_error = ""
            return cls(service=service)
        except GoogleAuthError as e:
            cls.last_error = f"Auth: {e}"
            logger.warning("[google-plugin] ContactsClient auth failed: %s", e)
            return None
        except Exception as e:
            cls.last_error = f"{type(e).__name__}: {e}"
            logger.warning("[google-plugin] ContactsClient build failed: %s: %s", type(e).__name__, e)
            return None

    def list_contacts(self, max_results: int = 50, sort_order: str = "LAST_NAME_ASCENDING") -> list:
        """List contacts with names, emails, and phone numbers."""
        result = self._service.people().connections().list(
            resourceName="people/me",
            pageSize=max_results,
            sortOrder=sort_order,
            personFields="names,emailAddresses,phoneNumbers,organizations,biographies",
        ).execute()
        return result.get("connections", [])

    def search_contacts(self, query: str, max_results: int = 20) -> list:
        """Search contacts by name, email, or phone."""
        result = self._service.people().searchContacts(
            query=query,
            pageSize=max_results,
            readMask="names,emailAddresses,phoneNumbers,organizations",
        ).execute()
        return [r.get("person", {}) for r in result.get("results", [])]

    def create_contact(
        self,
        first_name: str,
        last_name: str = "",
        email: str = "",
        phone: str = "",
        organization: str = "",
        title: str = "",
    ) -> dict:
        """Create a new contact."""
        person = {"names": [{"givenName": first_name, "familyName": last_name}]}

        if email:
            person["emailAddresses"] = [{"value": email}]
        if phone:
            person["phoneNumbers"] = [{"value": phone}]
        if organization or title:
            org = {}
            if organization:
                org["name"] = organization
            if title:
                org["title"] = title
            person["organizations"] = [org]

        return self._service.people().createContact(body=person).execute()

    def get_contact(self, resource_name: str) -> dict:
        """Get a specific contact by resource name."""
        return self._service.people().get(
            resourceName=resource_name,
            personFields="names,emailAddresses,phoneNumbers,organizations,biographies,addresses",
        ).execute()


def format_contact(person: dict) -> str:
    """Format a single contact for display."""
    names = person.get("names", [{}])
    display_name = names[0].get("displayName", "Unknown") if names else "Unknown"

    parts = [f"**{display_name}**"]

    emails = person.get("emailAddresses", [])
    if emails:
        email_str = ", ".join(e.get("value", "") for e in emails)
        parts.append(f"  Email: {email_str}")

    phones = person.get("phoneNumbers", [])
    if phones:
        phone_str = ", ".join(p.get("value", "") for p in phones)
        parts.append(f"  Phone: {phone_str}")

    orgs = person.get("organizations", [])
    if orgs:
        org = orgs[0]
        org_parts = []
        if org.get("title"):
            org_parts.append(org["title"])
        if org.get("name"):
            org_parts.append(org["name"])
        if org_parts:
            parts.append(f"  Organization: {' at '.join(org_parts)}")

    resource = person.get("resourceName", "")
    if resource:
        parts.append(f"  ID: {resource}")

    return "\n".join(parts)


def format_contact_list(contacts: list) -> str:
    """Format a list of contacts for display."""
    if not contacts:
        return "No contacts found."
    return "\n\n".join(format_contact(c) for c in contacts)
