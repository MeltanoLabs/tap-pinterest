"""Pinterest Authentication."""

from __future__ import annotations

import sys

from singer_sdk.authenticators import OAuthAuthenticator, SingletonMeta

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


# The SingletonMeta metaclass makes all streams reuse the same authenticator instance.
class PinterestAuthenticator(OAuthAuthenticator, metaclass=SingletonMeta):
    """Authenticator class for Pinterest."""

    @override
    @property
    def oauth_request_body(self) -> dict:
        """Define the OAuth request body for the Pinterest API.

        Returns:
            A dict with the request body.
        """
        return {
            "grant_type": "refresh_token",
            "refresh_token": self.config.get("refresh_token"),
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
