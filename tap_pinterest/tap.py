"""Pinterest tap class."""

from __future__ import annotations

import sys

from singer_sdk import Tap
from singer_sdk import typing as th

from tap_pinterest import streams

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


class TapPinterest(Tap):
    """Singer tap for Pinterest."""

    name = "tap-pinterest"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "client_id",
            th.StringType(nullable=False),
            secret=True,
            title="Client ID",
            description="Pinterest OAuth2 application client ID",
        ),
        th.Property(
            "client_secret",
            th.StringType(nullable=False),
            secret=True,
            title="Client Secret",
            description="Pinterest OAuth2 application client secret",
        ),
        th.Property(
            "refresh_token",
            th.StringType(nullable=False),
            secret=True,
            title="Refresh Token",
            description="Pinterest OAuth2 refresh token",
        ),
        th.Property(
            "api_url",
            th.StringType(nullable=False),
            default="https://api.pinterest.com/v5",
            title="API URL",
            description="Pinterest API URL",
        ),
        th.Property(
            "access_token",
            th.StringType(),
            secret=True,
            title="Pinterest Access Token",
            description="Skips the OAuth flow to access the API directly",
        ),
        th.Property(
            "oauth_credentials",
            th.ObjectType(
                th.Property(
                    "refresh_proxy_url",
                    th.StringType(nullable=False),
                    required=True,
                    description="Proxy URL to refresh the access token without client credentials",
                ),
                th.Property(
                    "refresh_proxy_url_auth",
                    th.StringType,
                    secret=True,
                    description="Authorization header value for the OAuth proxy URL",
                ),
                th.Property(
                    "access_token",
                    th.StringType,
                    secret=True,
                    description="Pinterest OAuth2 access token",
                ),
                th.Property(
                    "refresh_token",
                    th.StringType(nullable=False),
                    required=True,
                    secret=True,
                    description="Pinterest OAuth2 refresh token",
                ),
            ),
            title="OAuth Credentials",
            description=(
                "OAuth credentials for Meltano Cloud proxy authentication. "
                "When provided, client_id and client_secret are not required."
            ),
        ),
        th.Property(
            "start_date",
            th.StringType,
            title="Start Date",
            description=(
                "Start date for analytics streams in YYYY-MM-DD format. "
                "Defaults to 30 days ago. Pinterest limits analytics to 90 days per request."
            ),
        ),
        th.Property(
            "end_date",
            th.StringType,
            title="End Date",
            description="End date for analytics streams in YYYY-MM-DD format. Defaults to today.",
        ),
        th.Property(
            "analytics_columns",
            th.ArrayType(th.StringType),
            title="Analytics Columns",
            description=(
                "List of metric columns to fetch for analytics streams. "
                "Defaults to a standard set of spend, impression, click, and engagement metrics."
            ),
        ),
        th.Property(
            "analytics_granularity",
            th.StringType,
            title="Analytics Granularity",
            default="DAY",
            description=(
                "Granularity for analytics streams. One of: DAY, HOUR, WEEK, MONTH. "
                "Defaults to DAY."
            ),
            allowed_values=["DAY", "HOUR", "WEEK", "MONTH"],
        ),
    ).to_dict()

    @override
    def discover_streams(self) -> list[streams.PinterestStream]:
        """Return a list of discovered streams."""
        return [
            streams.PinsStream(self),
            streams.PinAnalyticsStream(self),
            streams.AdAccountsStream(self),
            streams.CampaignsStream(self),
            streams.CampaignAnalyticsStream(self),
            streams.AdGroupsStream(self),
            streams.AdsStream(self),
            streams.AdAnalyticsStream(self),
        ]


if __name__ == "__main__":
    TapPinterest.cli()
