"""Tests standard tap features using the built-in SDK tests library."""

import datetime
import json
import os

from requests import Response
from singer_sdk.testing import get_tap_test_class

from tap_pinterest.client import PinterestPaginator
from tap_pinterest.tap import TapPinterest

CI = "CI" in os.environ


def _one_week_ago() -> str:
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    return dt.strftime("%Y-%m-%d")


SAMPLE_CONFIG = {
    "start_date": _one_week_ago(),
}


# Run standard built-in tap tests from the SDK:
TestTapPinterest = get_tap_test_class(
    tap_class=TapPinterest,
    config=SAMPLE_CONFIG,
    include_tap_tests=not CI,
    include_stream_tests=not CI,
    include_stream_attribute_tests=not CI,
)


def test_pinterest_paginator() -> None:
    """Test the custom Pinterest paginator."""
    paginator = PinterestPaginator()

    response = Response()
    response._content = json.dumps({"items": [], "bookmark": "next-page"}).encode()  # noqa: SLF001

    paginator.advance(response)
    assert not paginator.finished
    assert paginator.current_value == "next-page"

    response._content = json.dumps({"items": [], "bookmark": None}).encode()  # noqa: SLF001
    paginator.advance(response)
    assert paginator.finished
