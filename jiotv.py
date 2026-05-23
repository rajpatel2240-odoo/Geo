import asyncio
import httpx
import orjson
import uvloop
from pathlib import Path

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

JSON_URL = "https://noisy-truth-6766.streamstar18.workers.dev/"
CACHE_FILE = "key_cache.json"

LICENSE_USER_AGENT = "OTT Navigator/1.7.4.1 (Linux;Android 11; en; 1tas50z)"

HEADERS = {
    "User-Agent": LICENSE_USER_AGENT
}

CONCURRENT_REQUESTS = 300
TIMEOUT = 2.5

sem = asyncio.Semaphore(CONCURRENT_REQUESTS)


# ---------------- CACHE ---------------- #

def load_cache():
    path = Path(CACHE_FILE)

    if not path.exists():
        return {}

    try:
        return orjson.loads(path.read_bytes())
    except:
        return {}


def save_cache(cache):
    Path(CACHE_FILE).write_bytes(
        orjson.dumps(cache)
    )


# ---------------- NETWORK ---------------- #

async def fetch_key(client, url):

    async with sem:

        try:
            r = await client.get(url)

            if r.status_code == 200:

                text = r.text.strip()

                if text:
                    return text

        except:
            pass

    return ""


# ---------------- CHANNEL ---------------- #

async def process_channel(client, channel, cache):

    name = channel.get("name", "Unknown")
    chan_id = channel.get("id", "")
    logo = channel.get("logo", "")
    group = channel.get("group", "Other")

    mpd = channel.get("mpd_url", "").replace(
        "|drmScheme=clearkey",
        ""
    )

    license_url = channel.get("license_url", "")

    cookie = channel.get("headers", {}).get("cookie", "")

    final_url = f"{mpd}?{cookie}" if cookie else mpd

    key = ""

    # ---------- CACHE HIT ----------
    if license_url in cache:
        key = cache[license_url]

    # ---------- FETCH ----------
    elif license_url and license_url != "null":

        key = await fetch_key(client, license_url)

        if key:
            cache[license_url] = key

    out = [
        f'#EXTINF:-1 tvg-id="{chan_id}" '
        f'tvg-name="{name}" '
        f'tvg-logo="{logo}" '
        f'group-title="{group}",{name}'
    ]

    if key:
        out.append(
            '#KODIPROP:inputstream.adaptive.license_type=clearkey'
        )

        out.append(
            f'#KODIPROP:inputstream.adaptive.license_key={key}'
        )

    out.append(final_url)

    return "\n".join(out)


# ---------------- MAIN ---------------- #

async def main():

    cache = load_cache()

    print(f"Loaded {len(cache)} cached keys")

    limits = httpx.Limits(
        max_connections=500,
        max_keepalive_connections=200
    )

    timeout = httpx.Timeout(TIMEOUT)

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=timeout,
        limits=limits,
        http2=True,
        follow_redirects=True
    ) as client:

        r = await client.get(JSON_URL)

        channels = orjson.loads(r.content)

        tasks = [
            process_channel(client, ch, cache)
            for ch in channels
        ]

        results = await asyncio.gather(*tasks)

    # Save updated cache
    save_cache(cache)

    with open("jiotv.m3u", "w", encoding="utf-8") as f:

        f.write("#EXTM3U\n")
        f.write("#Credits 🙏: cloudplay\n")
        f.write("#Telegram: https://t.me/cloudply\n\n")

        f.write("\n\n".join(results))

    print(f"Channels: {len(channels)}")
    print(f"Cached keys: {len(cache)}")
    print("Done")


if __name__ == "__main__":
    asyncio.run(main())
