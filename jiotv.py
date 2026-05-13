import requests
import json
import sys
import zlib

try:
    import brotli
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False

try:
    import zstandard as zstd
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

# --- Source URLs ---
CHANNELS_URL = "https://allinonereborn.online/jtv-fetch/jstr4web.json"
COOKIE_URL   = "https://allinonereborn.online/jstrweb2/cookies.json"
STATUS_URL   = "https://allinonereborn.online/jtv-fetch/jstarcookie/cookie.json"

OUTPUT_FILE  = "jiotv.m3u"

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "accept-encoding": "gzip, deflate, br, zstd",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=0, i",
    "referer": "https://allinonereborn-livetv-hub.pages.dev/",
    "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "cross-site",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "dnt": "1",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def try_decompress(data):
    """Try every known compression format and return decoded text."""
    try:
        return data.decode("utf-8")
    except Exception:
        pass
    if HAS_BROTLI:
        try:
            return brotli.decompress(data).decode("utf-8")
        except Exception:
            pass
    if HAS_ZSTD:
        try:
            return zstd.ZstdDecompressor().decompress(data).decode("utf-8")
        except Exception:
            pass
    try:
        return zlib.decompress(data, zlib.MAX_WBITS | 16).decode("utf-8")
    except Exception:
        pass
    try:
        return zlib.decompress(data).decode("utf-8")
    except Exception:
        pass
    try:
        return zlib.decompress(data, -zlib.MAX_WBITS).decode("utf-8")
    except Exception:
        pass
    return None


def fetch_json(url):
    resp = SESSION.get(url, timeout=15, allow_redirects=True)
    if resp.status_code != 200:
        print(f"ERROR: HTTP {resp.status_code} for {url}")
        sys.exit(1)
    if not resp.content:
        print(f"ERROR: Empty response from {url}")
        sys.exit(1)
    text = try_decompress(resp.content)
    if text is None:
        print(f"ERROR: Could not decompress response from {url}")
        sys.exit(1)
    try:
        return json.loads(text.strip())
    except Exception as e:
        print(f"ERROR: JSON decode failed for {url} — {e}")
        sys.exit(1)


def main():
    print("Fetching channel list ...")
    channels = fetch_json(CHANNELS_URL)
    if not isinstance(channels, list):
        channels = [channels]
    print(f"  {len(channels)} channels found.")

    print("Fetching cookie ...")
    cookie_data = fetch_json(COOKIE_URL)
    cookie_str = ""
    for item in cookie_data:
        if "cookie" in item:
            cookie_str = item["cookie"]
            break
    print(f"  Cookie: {cookie_str[:40]}...")

    print("Fetching channel status / final URLs ...")
    raw_status = fetch_json(STATUS_URL)

    status_map = {}
    if isinstance(raw_status, list):
        for entry in raw_status:
            cid = str(entry.get("channel_id", ""))
            final_url = entry.get("error_details", {}).get("final_url", "")
            if cid and final_url:
                status_map[cid] = final_url
    elif isinstance(raw_status, dict):
        for entry in raw_status.get("channels", [raw_status]):
            cid = str(entry.get("channel_id", ""))
            final_url = entry.get("error_details", {}).get("final_url", "")
            if cid and final_url:
                status_map[cid] = final_url
    print(f"  {len(status_map)} channel(s) with a final_url.")

    # --- Build M3U ---
    lines = ["#EXTM3U\n"]

    for ch in channels:
        ch_id    = str(ch.get("id", ""))
        name     = ch.get("name", "Unknown")
        category = ch.get("category", "")
        logo     = ch.get("logo", "")
        base_url = ch.get("url", "")
        key_id   = ch.get("keyId", "")
        key      = ch.get("key", "")

        if ch_id in status_map:
            stream_url = status_map[ch_id]
        else:
            stream_url = f"{base_url}?{cookie_str}"

        extinf = (
            f'#EXTINF:-1 '
            f'tvg-id="{ch_id}" '
            f'tvg-name="{name}" '
            f'tvg-logo="{logo}" '
            f'group-title="{category}" '
            f',{name}'
        )

        lines.append(extinf + "\n")
        if key_id and key:
            lines.append("#KODIPROP:inputstream.adaptive.license_type=clearkey\n")
            lines.append(f'#KODIPROP:inputstream.adaptive.license_key={{"keys":[{{"kty":"oct","k":"{key}","kid":"{key_id}"}}],"type":"temporary"}}\n')
        lines.append(stream_url + "\n")
        lines.append("\n")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\nDone! '{OUTPUT_FILE}' written with {len(channels)} channels.")


if __name__ == "__main__":
    main()
