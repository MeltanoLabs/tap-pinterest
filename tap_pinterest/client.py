"""REST client handling, including PinterestStream base class."""

from __future__ import annotations

import decimal
import sys
from functools import cached_property
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any

from singer_sdk import OpenAPISchema, StreamSchema, Stream
from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.pagination import BaseAPIPaginator
from singer_sdk.streams import RESTStream

from tap_pinterest.auth import PinterestAuthenticator

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

if TYPE_CHECKING:
    from collections.abc import Iterable

    import requests
    from singer_sdk.helpers.types import Auth, Context



class PinterestSchema(StreamSchema):
    @override
    def get_stream_schema(self, stream: Stream, stream_class: type[Stream]):
        schema = super().get_stream_schema(stream, stream_class)

        # Remove problematic field
        if stream.name == "ad_groups":
            schema["properties"].pop("dca_assets", None)
        return schema


#: Shared OpenAPI schema source pointing to the bundled Pinterest v5 spec.
OPENAPI = OpenAPISchema(resources.files("tap_pinterest") / "openapi.json")


class PinterestPaginator(BaseAPIPaginator):
    """Cursor-based paginator for Pinterest API using bookmark tokens."""

    def has_more(self, response: requests.Response) -> bool:
        """Return True if the response contains a bookmark for the next page."""
        return bool(response.json().get("bookmark"))

    @override
    def get_next(self, response: requests.Response) -> str | None:
        """Extract the bookmark cursor from the response."""
        return response.json().get("bookmark") or None


class PinterestStream(RESTStream):
    """Pinterest stream class."""

    # List endpoints return {"items": [...], "bookmark": "..."}
    records_jsonpath = "$.items[*]"

    @override
    @property
    def url_base(self) -> str:
        """Return the Pinterest API v5 base URL."""
        return "https://api.pinterest.com/v5"

    @override
    @cached_property
    def authenticator(self) -> Auth:
        """Return a new authenticator object."""
        return PinterestAuthenticator(
            client_id=self.config["client_id"],
            client_secret=self.config["client_secret"],
            auth_endpoint="https://api.pinterest.com/v5/oauth/token",
            oauth_scopes="ads:read",
        )

    @override
    def get_new_paginator(self) -> BaseAPIPaginator:
        """Return a cursor-based paginator for Pinterest list endpoints."""
        return PinterestPaginator(start_value=None)

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
