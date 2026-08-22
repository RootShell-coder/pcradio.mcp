"""Read-only live check for the normalized user playlist."""

import asyncio

from pcradio_mcp.client import PCRadioClient
from pcradio_mcp.config import Settings


async def main() -> None:
    settings = Settings()
    result = await PCRadioClient(
        settings.pcradio_base_url, settings.pcradio_timeout
    ).user_playlist()
    assert isinstance(result.get("total"), int)
    assert result["total"] == len(result.get("stations", []))
    assert all("url" not in station for station in result.get("stations", []))
    print(f"get_pcradio_user_playlist: OK ({result['total']} stations)")


if __name__ == "__main__":
    asyncio.run(main())
