"""Pinterest Authentication."""

from __future__ import annotations

import datetime
import sys
from typing import Any

import requests
from singer_sdk.authenticators import OAuthAuthenticator, SingletonMeta

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


class PinterestAuthenticator(OAuthAuthenticator, metaclass=SingletonMeta):
    """Authenticator class for Pinterest using standard OAuth2 (client ID + secret)."""

    def __init__(self, *args: Any, refresh_token: str | None, **kwargs: Any) -> None:
        """Initialize Pinterest authenticator."""
        super().__init__(*args, **kwargs)
        self.refresh_token = refresh_token

    @override
    @property
    def oauth_request_body(self) -> dict:
        """Define the OAuth request body for the Pinterest API.

        Returns:
            A dict with the request body.
        """
        return {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }


class PinterestProxyAuthenticator(OAuthAuthenticator, metaclass=SingletonMeta):
    """Authenticator for Meltano Cloud proxy OAuth (no client ID/secret required).

    Refreshes tokens by POSTing to a proxy URL that handles client credentials
    server-side.
    """

    @override
    @property
    def oauth_request_body(self) -> dict:
        """Define the OAuth request body for the proxy endpoint.

        Returns:
            A dict with the request body.
        """
        return {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }

    @override
    def update_access_token(self) -> None:
        """Request a new access token from the OAuth proxy URL.

        Raises:
            RuntimeError: When token refresh fails.
        """
        self.logger.info("Requesting new access token via OAuth proxy")
        request_time = datetime.datetime.now(tz=datetime.timezone.utc)

        token_response = requests.post(
            self.auth_endpoint,
            headers=self._oauth_headers,
            json=self.oauth_request_body,
            timeout=60,
        )
        try:
            token_response.raise_for_status()
        except requests.HTTPError as ex:
            self.handle_error(
                content=ex.response.text,
                status_code=ex.response.status_code,
            )
            msg = f"Failed to update access token via proxy (status={ex.response.status_code})"
            raise RuntimeError(msg) from ex

        token_json = token_response.json()
        self.access_token = token_json["access_token"]
        expiration = token_json.get("expires_in", self._default_expiration)
        self.expires_in = int(expiration) if expiration else None
        self.last_refreshed = request_time
