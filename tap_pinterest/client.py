"""REST client handling, including PinterestStream base class."""

from __future__ import annotations

import base64
import sys
from functools import cached_property
from importlib import resources
from typing import TYPE_CHECKING, Any

from singer_sdk import OpenAPISchema, StreamSchema
from singer_sdk.authenticators import BearerTokenAuthenticator
from singer_sdk.pagination import BaseAPIPaginator
from singer_sdk.streams import RESTStream

from tap_pinterest.auth import PinterestAuthenticator, PinterestProxyAuthenticator

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

if TYPE_CHECKING:
    import requests
    from singer_sdk import Stream
    from singer_sdk.helpers.types import Auth, Context


def basic_creds_encode(username: str, password: str, /) -> str:
    """Encode a username and password as base64 for basic authentication."""
    return base64.b64encode(f"{username}:{password}".encode()).decode()


class PinterestSchema(StreamSchema):
    """Schema override for the Pinterest OpenAPI spec."""

    @override
    def get_stream_schema(self, stream: Stream, stream_class: type[Stream]) -> dict:
        schema = super().get_stream_schema(stream, stream_class)

        # Remove problematic field
        if stream.name == "ad_groups":
            schema["properties"].pop("dca_assets", None)
        return schema


#: Shared OpenAPI schema source pointing to the bundled Pinterest v5 spec.
OPENAPI = OpenAPISchema(resources.files("tap_pinterest") / "openapi.json")


class PinterestPaginator(BaseAPIPaginator[str | None]):
    """Cursor-based paginator for Pinterest API using bookmark tokens."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize paginator."""
        kwargs.setdefault("start_value", None)
        super().__init__(*args, **kwargs)

    @override
    def get_next(self, response: requests.Response) -> str | None:
        """Extract the bookmark cursor from the response."""
        return response.json().get("bookmark")


class PinterestStream(RESTStream):
    """Pinterest stream class."""

    # List endpoints return {"items": [...], "bookmark": "..."}
    records_jsonpath = "$.items[*]"

    @override
    @property
    def url_base(self) -> str:
        """Return the Pinterest API v5 base URL."""
        return self.config["api_url"]

    @override
    @cached_property
    def authenticator(self) -> Auth:
        """Return a new authenticator object."""
        if access_token := self.config.get("access_token"):
            return BearerTokenAuthenticator(token=access_token)

        if oauth_creds := self.config.get("oauth_credentials"):
            headers: dict[str, str] = {}
            if auth_header := oauth_creds.get("refresh_proxy_url_auth"):
                headers["Authorization"] = auth_header
            authenticator = PinterestProxyAuthenticator(
                auth_endpoint=oauth_creds["refresh_proxy_url"],
                oauth_headers=headers,
            )
            authenticator.refresh_token = oauth_creds["refresh_token"]
            if access_token := oauth_creds.get("access_token"):
                authenticator.access_token = access_token
            return authenticator

        credentials = basic_creds_encode(self.config["client_id"], self.config["client_secret"])
        return PinterestAuthenticator(
            auth_endpoint=f"{self.url_base}/oauth/token",
            oauth_scopes="ads:read",
            oauth_headers={"Authorization": f"Basic {credentials}"},
            refresh_token=self.config["refresh_token"],
        )

    @override
    def get_new_paginator(self) -> BaseAPIPaginator:
        """Return a cursor-based paginator for Pinterest list endpoints."""
        return PinterestPaginator()

    @override
    def get_url_params(
        self,
        context: Context | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        """Return URL query parameters, including pagination cursor if present."""
        params: dict[str, Any] = {"page_size": 250}
        if next_page_token:
            params["bookmark"] = next_page_token
        return params
