#!/usr/bin/env python3
"""
Kleiner Wrapper um die Firecrawl Scrape API.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


DEFAULT_LANGUAGES = {
    "AT": ["de-AT", "de", "en-US"],
    "CH": ["de-CH", "de", "fr-CH", "it-CH", "en-US"],
    "DE": ["de-DE", "de", "en-US"],
    "ES": ["es-ES", "es", "en-US"],
    "FR": ["fr-FR", "fr", "en-US"],
    "GR": ["el-GR", "el", "en-US"],
    "IT": ["it-IT", "it", "en-US"],
    "PT": ["pt-PT", "pt", "en-US"],
}


class FirecrawlClient:
    """Sehr dünner HTTP-Client für Firecrawl."""

    API_URL = "https://api.firecrawl.dev/v2/scrape"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._discover_api_key()
        self.session = requests.Session()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _discover_api_key(self) -> Optional[str]:
        env_key = os.getenv("FIRECRAWL_API_KEY")
        if env_key:
            return env_key

        for path in (
            Path("/etc/traktor-finder.env"),
            Path(__file__).resolve().parent / ".env",
        ):
            key = self._read_key_from_file(path)
            if key:
                return key

        return None

    @staticmethod
    def _read_key_from_file(path: Path) -> Optional[str]:
        if not path.exists():
            return None

        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() != "FIRECRAWL_API_KEY":
                    continue
                return value.strip().strip('"').strip("'")
        except OSError:
            return None

        return None

    def scrape(
        self,
        *,
        url: str,
        country_code: Optional[str] = None,
        wait_for: int = 8000,
        timeout_ms: int = 120000,
        actions: Optional[List[Dict[str, Any]]] = None,
        formats: Optional[List[str]] = None,
        proxy: str = "auto",
        only_main_content: bool = False,
    ) -> Dict[str, Any]:
        if not self.is_configured:
            raise RuntimeError("FIRECRAWL_API_KEY ist nicht gesetzt")

        payload: Dict[str, Any] = {
            "url": url,
            "formats": formats or ["html", "rawHtml", "links"],
            "onlyMainContent": only_main_content,
            "timeout": timeout_ms,
            "waitFor": wait_for,
            "proxy": proxy,
            "maxAge": 0,
        }

        if actions:
            payload["actions"] = actions

        if country_code:
            payload["location"] = {
                "country": country_code,
                "languages": DEFAULT_LANGUAGES.get(country_code, ["en-US", "en"]),
            }

        response = self.session.post(
            self.API_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=max(90, int(timeout_ms / 1000) + 30),
        )
        response.raise_for_status()

        body = response.json()
        if not body.get("success"):
            raise RuntimeError(body.get("error") or "Firecrawl scrape fehlgeschlagen")

        return body.get("data") or {}

    def fetch_html(
        self,
        *,
        url: str,
        country_code: Optional[str] = None,
        wait_for: int = 8000,
        timeout_ms: int = 120000,
        actions: Optional[List[Dict[str, Any]]] = None,
        proxy: str = "auto",
        only_main_content: bool = False,
    ) -> str:
        data = self.scrape(
            url=url,
            country_code=country_code,
            wait_for=wait_for,
            timeout_ms=timeout_ms,
            actions=actions,
            proxy=proxy,
            only_main_content=only_main_content,
        )
        return data.get("html") or data.get("rawHtml") or ""
