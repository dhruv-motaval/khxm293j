import asyncio
from datetime import datetime, timezone

import httpx

from app.elexon import _get_rows

UTC = timezone.utc


def test_dataset_stream_uses_publication_time_filters():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=[{"publishTime": "2026-01-01T00:00:00Z"}])

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            rows = await _get_rows(
                client,
                "WINDFOR",
                datetime(2025, 12, 30, tzinfo=UTC),
                datetime(2026, 2, 2, tzinfo=UTC),
            )
            assert len(rows) == 1

    asyncio.run(run())
    assert "publishDateTimeFrom=2025-12-30T00%3A00%3A00Z" in captured["url"]
    assert "publishDateTimeTo=2026-02-02T00%3A00%3A00Z" in captured["url"]
