from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
from typing import Any

from jarvis.core.config import GoogleConfig


LOGGER = logging.getLogger(__name__)


class GoogleWorkspaceGateway:
    CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
    CONTACT_SCOPE = "https://www.googleapis.com/auth/contacts.readonly"

    def __init__(self, config: GoogleConfig) -> None:
        self._config = config

    def is_enabled(self) -> bool:
        return self._config.enabled and bool(self._config.credentials_path)

    def upcoming_events(self, max_results: int = 5) -> tuple[bool, str, list[dict[str, Any]]]:
        service = self._build_service("calendar", "v3", [self.CALENDAR_SCOPE])
        if service is None:
            return False, "Google Calendar integration is not configured.", []

        now = dt.datetime.utcnow().isoformat() + "Z"
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        if not events:
            return True, "No upcoming calendar events found.", []

        normalized = []
        for event in events:
            start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date", "")
            normalized.append({"summary": event.get("summary", "Untitled event"), "start": start})

        summary = "; ".join(f"{item['summary']} at {item['start']}" for item in normalized[:3])
        return True, f"Upcoming events: {summary}", normalized

    def search_contacts(self, query: str, max_results: int = 5) -> tuple[bool, str, list[dict[str, Any]]]:
        service = self._build_service("people", "v1", [self.CONTACT_SCOPE])
        if service is None:
            return False, "Google Contacts integration is not configured.", []

        results = (
            service.people()
            .searchContacts(
                query=query,
                pageSize=max_results,
                readMask="names,emailAddresses,phoneNumbers",
            )
            .execute()
        )
        contacts = results.get("results", [])
        if not contacts:
            return True, f"No contacts found for {query}.", []

        normalized = []
        for contact in contacts:
            person = contact.get("person", {})
            names = person.get("names", [{}])
            emails = person.get("emailAddresses", [{}])
            phones = person.get("phoneNumbers", [{}])
            normalized.append(
                {
                    "name": names[0].get("displayName", "Unknown"),
                    "email": emails[0].get("value", ""),
                    "phone": phones[0].get("value", ""),
                }
            )

        summary = "; ".join(item["name"] for item in normalized[:3])
        return True, f"Contacts found: {summary}", normalized

    def _build_service(self, api_name: str, api_version: str, scopes: list[str]) -> Any | None:
        if not self.is_enabled():
            return None

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except Exception:
            LOGGER.exception("Google API dependencies are not installed")
            return None

        credentials_path = Path(self._config.credentials_path).expanduser()

        # Use a per-scope token file so calendar and contacts credentials don't collide.
        if self._config.token_path:
            base_token_path = Path(self._config.token_path).expanduser()
        else:
            base_token_path = credentials_path.with_name("token.json")

        scope_suffix = "_".join(s.rstrip("/").split("/")[-1] for s in scopes)
        token_path = base_token_path.with_stem(f"{base_token_path.stem}_{scope_suffix}")

        creds = None
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), scopes)
            except Exception:
                LOGGER.exception("Failed to load Google token file")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    LOGGER.exception("Failed to refresh Google credentials")
                    creds = None
            elif credentials_path.exists():
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
                    creds = flow.run_local_server(port=0)
                except Exception:
                    LOGGER.exception("Google OAuth flow failed")
                    creds = None

            if creds is not None:
                try:
                    token_path.write_text(creds.to_json(), encoding="utf-8")
                except Exception:
                    LOGGER.exception("Failed to persist Google token")

        if creds is None:
            return None

        try:
            return build(api_name, api_version, credentials=creds, cache_discovery=False)
        except Exception:
            LOGGER.exception("Failed to build Google API service for %s", api_name)
            return None
