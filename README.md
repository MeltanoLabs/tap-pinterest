# tap-pinterest

`tap-pinterest` is a Singer tap for the [Pinterest Ads API v5](https://developers.pinterest.com/docs/api/v5/introduction/).

Built with the [Meltano Singer SDK](https://sdk.meltano.com).

## TODO

- [ ] Run integration tests in CI
- [ ] Confirm that `refresh_token` is indeed a required setting (vs. deriving it from the OAuth2 flow automatically)
- [ ] Add [Meltano Cloud OAuth2 support](https://docs.meltano.com/cloud/concepts/oauth)

## Streams

| Stream | Endpoint | Replication |
|:-------|:---------|:------------|
| `ad_accounts` | `GET /ad_accounts` | Full |
| `campaigns` | `GET /ad_accounts/{id}/campaigns` | Incremental (`updated_time`) |
| `ad_groups` | `GET /ad_accounts/{id}/ad_groups` | Incremental (`updated_time`) |
| `ads` | `GET /ad_accounts/{id}/ads` | Incremental (`updated_time`) |
| `campaign_analytics` | `GET /ad_accounts/{id}/campaigns/analytics` | Full |
| `ad_analytics` | `GET /ad_accounts/{id}/ads/analytics` | Full |

`campaigns`, `ad_groups`, `ads`, `campaign_analytics`, and `ad_analytics` are child streams of `ad_accounts` and are extracted for every ad account the authenticated user has access to.

Analytics streams return records with identity fields at the top level and all requested metric values nested under a `metrics` object:

```json
{
  "CAMPAIGN_ID": "549755885175",
  "DATE": "2024-01-15",
  "metrics": {
    "SPEND_IN_DOLLAR": 42.50,
    "TOTAL_CLICKTHROUGH": 312,
    "CTR": 0.038
  }
}
```

## Installation

Install from PyPI:

```bash
uv tool install tap-pinterest
```

Install from GitHub:

```bash
uv tool install git+https://github.com/MeltanoLabs/tap-pinterest.git@main
```

## Configuration

### Accepted Config Options

| Setting | Required | Default | Description |
|:--------|:--------:|:-------:|:------------|
| `client_id` | ✅ | — | Pinterest OAuth2 application client ID |
| `client_secret` | ✅ | — | Pinterest OAuth2 application client secret |
| `refresh_token` | ✅ | — | Pinterest OAuth2 refresh token |
| `start_date` | | 30 days ago | Start date for analytics streams (`YYYY-MM-DD`). Pinterest limits analytics requests to 90 days. |
| `end_date` | | Today | End date for analytics streams (`YYYY-MM-DD`). |
| `analytics_columns` | | See below | List of metric columns to include in analytics streams. |
| `analytics_granularity` | | `DAY` | Time granularity for analytics streams. One of `TOTAL`, `DAY`, `HOUR`, `WEEK`, `MONTH`. |

A full list of supported settings and capabilities is available by running:

```bash
tap-pinterest --about
```

### Default analytics columns

When `analytics_columns` is not set, the following columns are requested:

```
SPEND_IN_DOLLAR, PAID_IMPRESSION, TOTAL_IMPRESSION, TOTAL_CLICKTHROUGH,
TOTAL_ENGAGEMENT, CTR, ECTR, CPC_IN_MICRO_DOLLAR, ECPC_IN_DOLLAR,
CAMPAIGN_ID, AD_GROUP_ID, AD_ID, PIN_ID, AD_ACCOUNT_ID,
CAMPAIGN_NAME, AD_GROUP_NAME, AD_NAME
```

See the [Pinterest Ads API documentation](https://developers.pinterest.com/docs/api/v5/ad_accounts-analytics/) for the full list of available columns.

### Authentication

This tap uses Pinterest's OAuth2 flow. You need:

- A **client ID** and **client secret** from a [Pinterest app](https://developers.pinterest.com/apps/).
- A **refresh token** obtained by completing the OAuth2 authorization code flow with the `ads:read` scope.

### Configure using environment variables

```bash
export TAP_PINTEREST_CLIENT_ID=your_client_id
export TAP_PINTEREST_CLIENT_SECRET=your_client_secret
export TAP_PINTEREST_REFRESH_TOKEN=your_refresh_token
export TAP_PINTEREST_START_DATE=2024-01-01
```

Alternatively, create a `config.json`:

```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "refresh_token": "your_refresh_token",
  "start_date": "2024-01-01"
}
```

## Usage

### Executing the tap directly

```bash
tap-pinterest --version
tap-pinterest --help
tap-pinterest --config config.json --discover > catalog.json
tap-pinterest --config config.json --catalog catalog.json
```

### Using with Meltano

```bash
# Install Meltano
uv tool install meltano

# Test invocation
meltano invoke tap-pinterest --version

# Run a test EL pipeline
meltano run tap-pinterest target-jsonl
```

## Developer Resources

### Initialize your development environment

Prerequisites: Python 3.10+, [uv](https://docs.astral.sh/uv/)

```bash
uv sync
```

### Run tests

```bash
uv run pytest
```

### SDK Dev Guide

See the [Singer SDK dev guide](https://sdk.meltano.com/en/latest/dev_guide.html) for more details on building taps.
