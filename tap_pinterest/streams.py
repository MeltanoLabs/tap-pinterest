"""Stream type classes for tap-pinterest."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, ClassVar

from singer_sdk.pagination import SinglePagePaginator

from tap_pinterest.client import OPENAPI, PinterestSchema, PinterestStream

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

if TYPE_CHECKING:
    import requests
    from singer_sdk.helpers.types import Context
    from singer_sdk.pagination import BaseAPIPaginator

# Default set of analytics metric columns to request when not configured.
DEFAULT_ANALYTICS_COLUMNS = [
    "SPEND_IN_DOLLAR",
    "PAID_IMPRESSION",
    "TOTAL_IMPRESSION",
    "TOTAL_CLICKTHROUGH",
    "TOTAL_ENGAGEMENT",
    "CTR",
    "ECTR",
    "CPC_IN_MICRO_DOLLAR",
    "ECPC_IN_DOLLAR",
    "CAMPAIGN_ID",
    "AD_GROUP_ID",
    "AD_ID",
    "PIN_ID",
    "AD_ACCOUNT_ID",
    "CAMPAIGN_NAME",
    "AD_GROUP_NAME",
    "AD_NAME",
]


DEFAULT_PIN_METRIC_TYPES = [
    "IMPRESSION",
    "OUTBOUND_CLICK",
    "PIN_CLICK",
    "SAVE",
    "SAVE_RATE",
]


class AdAccountsStream(PinterestStream):
    """Ad Accounts stream — lists all ad accounts accessible to the user."""

    name = "ad_accounts"
    path = "/ad_accounts"
    primary_keys = ("id",)
    replication_key = None

    schema = PinterestSchema(OPENAPI, key="AdAccount")

    @override
    def get_child_context(self, record: dict, context: Context | None) -> dict:
        """Return context for child streams containing the ad account ID."""
        return {"ad_account_id": record["id"]}


class CampaignsStream(PinterestStream):
    """Campaigns stream — lists all campaigns within an ad account."""

    name = "campaigns"
    path = "/ad_accounts/{ad_account_id}/campaigns"
    primary_keys = ("id",)
    replication_key = "updated_time"
    parent_stream_type = AdAccountsStream

    schema = PinterestSchema(OPENAPI, key="CampaignResponse")

    @override
    def get_child_context(self, record: dict, context: Context | None) -> dict:
        assert context is not None  # noqa: S101
        return {
            "ad_account_id": context["ad_account_id"],
            "campaign_id": record["id"],
        }


class AdGroupsStream(PinterestStream):
    """Ad Groups stream — lists all ad groups within an ad account."""

    name = "ad_groups"
    path = "/ad_accounts/{ad_account_id}/ad_groups"
    primary_keys = ("id",)
    replication_key = "updated_time"
    parent_stream_type = AdAccountsStream

    schema = PinterestSchema(OPENAPI, key="AdGroupResponse")


class AdsStream(PinterestStream):
    """Ads stream — lists all ads within an ad account."""

    name = "ads"
    path = "/ad_accounts/{ad_account_id}/ads"
    primary_keys = ("id",)
    replication_key = "updated_time"
    parent_stream_type = AdAccountsStream

    schema = PinterestSchema(OPENAPI, key="AdResponse")

    @override
    def get_child_context(self, record: dict, context: Context | None) -> dict:
        assert context is not None  # noqa: S101
        return {
            "ad_account_id": context["ad_account_id"],
            "ad_id": record["id"],
        }


class PinsStream(PinterestStream):
    """Pins stream — lists all pins created by the authenticated user."""

    name = "pins"
    path = "/pins"
    primary_keys = ("id",)
    replication_key = "created_at"

    schema = PinterestSchema(OPENAPI, key="Pin")

    @override
    def get_child_context(self, record: dict, context: Context | None) -> dict:
        """Return context for child streams containing the pin ID."""
        return {"pin_id": record["id"]}


_METRICS_PROPERTY: dict = {
    "type": "object",
    "description": "Requested metric values keyed by column name.",
    "additionalProperties": True,
}


class _AnalyticsStream(PinterestStream):
    """Base class for Pinterest analytics streams.

    Analytics streams are not paginated and require ``start_date``, ``end_date``,
    ``columns``, and ``granularity`` query parameters.

    The API returns all metric columns at the top level of each row alongside the
    entity ID and date.  This class reshapes each record so that the identity fields
    stay at the top level while all metric values are nested under a ``metrics``
    object, making it easier to work with in downstream tools.
    """

    # Analytics endpoints return a plain array, not a paginated {"items": [...]}
    records_jsonpath = "$[*]"
    replication_key = "DATE"

    #: Column names that remain at the top level of the record (not moved to metrics).
    _identity_keys: ClassVar[frozenset[str]] = frozenset({"DATE"})

    @override
    def get_new_paginator(self) -> BaseAPIPaginator:
        """Analytics endpoints are not paginated."""
        return SinglePagePaginator()

    @override
    def get_url_params(
        self,
        context: Context | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        """Return URL parameters including required analytics fields."""
        ninety_days_ago = datetime.now(tz=timezone.utc) - timedelta(days=90)
        if bookmark := self.get_starting_timestamp(context):
            start_date = max(bookmark, ninety_days_ago)
        else:
            start_date = ninety_days_ago

        end_date = self.config.get(
            "end_date",
            datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        )

        columns = self.config.get("analytics_columns", DEFAULT_ANALYTICS_COLUMNS)
        granularity = self.config.get("analytics_granularity", "DAY")
        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date,
            "columns": columns,
            "granularity": granularity,
        }

    @override
    def post_process(self, row: dict, context: Context | None = None) -> dict | None:
        """Nest all metric columns under a ``metrics`` object field."""
        identity = {k: v for k, v in row.items() if k in self._identity_keys}
        metrics = {k: v for k, v in row.items() if k not in self._identity_keys}
        return {**identity, "metrics": metrics}


class CampaignAnalyticsStream(_AnalyticsStream):
    """Campaign Analytics stream — daily/aggregated metrics per campaign."""

    name = "campaign_analytics"
    path = "/ad_accounts/{ad_account_id}/campaigns/analytics"
    primary_keys = ("CAMPAIGN_ID",)
    parent_stream_type = CampaignsStream

    _identity_keys: ClassVar[frozenset[str]] = frozenset({"CAMPAIGN_ID", "DATE"})

    schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "CAMPAIGN_ID": {
                "type": "string",
                "description": "The ID of the campaign these metrics belong to.",
            },
            "DATE": {
                "type": "string",
                "format": "date-time",
                "description": "Metrics date.",
            },
            "metrics": _METRICS_PROPERTY,
        },
        "required": ["CAMPAIGN_ID"],
    }

    @override
    def get_url_params(
        self,
        context: Context | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        assert context is not None  # noqa: S101
        params = super().get_url_params(context, next_page_token)
        params["campaign_ids"] = [context["campaign_id"]]
        return params


class AdAnalyticsStream(_AnalyticsStream):
    """Ad Analytics stream — daily/aggregated metrics per ad."""

    name = "ad_analytics"
    path = "/ad_accounts/{ad_account_id}/ads/analytics"
    primary_keys = ("AD_ID",)
    parent_stream_type = AdsStream

    _identity_keys: ClassVar[frozenset[str]] = frozenset({"AD_ID", "DATE"})

    schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "AD_ID": {
                "type": "string",
                "description": "The ID of the ad these metrics belong to.",
            },
            "DATE": {
                "type": "string",
                "format": "date-time",
                "description": "Metrics date.",
            },
            "metrics": _METRICS_PROPERTY,
        },
        "required": ["AD_ID"],
    }

    @override
    def get_url_params(
        self,
        context: Context | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        assert context is not None  # noqa: S101
        params = super().get_url_params(context, next_page_token)
        params["ad_ids"] = [context["ad_id"]]
        return params


class PinAnalyticsStream(_AnalyticsStream):
    """Pin Analytics stream — daily organic metrics per pin.

    The API response is a dict keyed by app_type (e.g. "TOTAL"), each containing
    a ``daily_metrics`` array.  This stream flattens that into one record per
    (pin_id, app_type, date).

    Note: this endpoint is disabled in the Pinterest sandbox (x-sandbox: disabled).
    """

    name = "pin_analytics"
    path = "/pins/{pin_id}/analytics"
    primary_keys = ("pin_id", "app_type", "date")
    replication_key = "date"
    parent_stream_type = PinsStream

    # _identity_keys not used — parse_response builds the record shape directly
    _identity_keys: ClassVar[frozenset[str]] = frozenset()

    schema: ClassVar[dict] = {
        "type": "object",
        "properties": {
            "pin_id": {"type": "string"},
            "app_type": {"type": "string"},
            "date": {"type": "string", "format": "date"},
            "metrics": {
                "type": "object",
                "additionalProperties": True,
                "description": "Metric values keyed by metric name.",
            },
        },
        "required": ["pin_id", "app_type", "date"],
    }

    @override
    def get_url_params(
        self,
        context: Context | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        params = super().get_url_params(context, next_page_token)
        # Pin analytics uses metric_types instead of columns/granularity
        params.pop("columns", None)
        params.pop("granularity", None)
        params["metric_types"] = DEFAULT_PIN_METRIC_TYPES
        return params

    @override
    def parse_response(self, response: requests.Response) -> list[dict]:
        """Flatten {app_type: {daily_metrics: [{date, metrics}]}} into records."""
        return [
            {"app_type": app_type, "date": day["date"], "metrics": day.get("metrics", {})}
            for app_type, app_data in response.json().items()
            for day in app_data.get("daily_metrics", [])
        ]

    @override
    def post_process(self, row: dict, context: Context | None = None) -> dict | None:
        """Add pin_id from parent context."""
        return {"pin_id": context["pin_id"] if context else None, **row}
