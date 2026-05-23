# Credits 🙏: cloudplay
# Telegram: https://t.me/cloudply

import asyncio
import aiohttp
import json

JSON_URL = "https://noisy-truth-6766.streamstar18.workers.dev/"
LICENSE_USER_AGENT = "OTT Navigator/1.7.4.1 (Linux;Android 11; en; 1tas50z)"

HEADERS = {
    "User-Agent": LICENSE_USER_AGENT
}

# Increase if server can handle it
MAX_CONCURRENT_REQUESTS = 100


async def fetch_key(session, license_url):
    try:
        async with session.get(
            license_url,
            timeout=aiohttp.ClientTimeout(total=5)
        ) as response:

            if response.status == 200:
                return (await response.text()).strip()

    except:
        pass

    return ""


async def process_channel(session, channel):
    name = channel.get("name", "Unknown Channel")
    chan_id = channel.get("id", "")
    logo = channel.get("logo", "")
    group = channel.get("group", "Uncategorized")

    raw_mpd = channel.get("mpd_url", "")
    license_url = channel.get("license_url", "")

    cookie = channel.get("headers", {}).get("cookie", "")

    clean_mpd = raw_mpd.replace("|drmScheme=clearkey", "")
    final_url = f"{clean_mpd}?{cookie}" if cookie else clean_mpd

    key = ""

    if license_url and license_url != "null":
        key = await fetch_key(session, license_url)

    lines = []

    lines.append(
        f'#EXTINF:-1 tvg-id="{chan_id}" '
        f'tvg-name="{name}" '
        f'tvg-logo="{logo}" '
        f'group-title="{group}",{name}'
    )

    if key:
        lines.append(
            '#KODIPROP:inputstream.adaptive.license_type=clearkey'
        )
        lines.append(
            f'#KODIPROP:inputstream.adaptive.license_key={key}'
        )

    lines.append(final_url)

    return "\n".join(lines)


async def generate_m3u(output_m3u_path):
    print(f"Fetching JSON data from: {JSON_URL}")

    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT_REQUESTS,
        ttl_dns_cache=300
    )

    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(
        headers=HEADERS,
        connector=connector,
        timeout=timeout
    ) as session:

        async with session.get(JSON_URL) as response:
            channels = await response.json()

        print(f"Loaded {len(channels)} channels")

        tasks = [
            process_channel(session, channel)
            for channel in channels
        ]

        results = await asyncio.gather(*tasks)

    with open(output_m3u_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("#Credits 🙏: cloudplay\n")
        f.write("#Telegram: https://t.me/cloudply\n\n")

        f.write("\n\n".join(results))

    print(f"Saved to {output_m3u_path}")


if __name__ == "__main__":
    asyncio.run(generate_m3u("jiotv.m3u"))
