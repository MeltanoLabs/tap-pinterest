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
            required=True,
            secret=True,
            title="Client ID",
            description="Pinterest OAuth2 application client ID",
        ),
        th.Property(
            "client_secret",
            th.StringType(nullable=False),
            required=True,
            secret=True,
            title="Client Secret",
            description="Pinterest OAuth2 application client secret",
        ),
        th.Property(
            "refresh_token",
            th.StringType(nullable=False),
            required=True,
            secret=True,
            title="Refresh Token",
            description="Pinterest OAuth2 refresh token",
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
                "Granularity for analytics streams. "
                "One of: DAY, HOUR, WEEK, MONTH. Defaults to DAY."
            ),
            allowed_values=["DAY", "HOUR", "WEEK", "MONTH"],
        ),
    ).to_dict()

    @override
    def discover_streams(self) -> list[streams.PinterestStream]:
        """Return a list of discovered streams."""
        return [
            streams.AdAccountsStream(self),
            streams.CampaignsStream(self),
            streams.AdGroupsStream(self),
            streams.AdsStream(self),
            streams.CampaignAnalyticsStream(self),
            streams.AdAnalyticsStream(self),
        ]


if __name__ == "__main__":
    TapPinterest.cli()
