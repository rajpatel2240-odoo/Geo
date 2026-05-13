import requests
import json
import sys
import zlib

# pip install brotli zstandard
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

OUTPUT_FILE  = "playlist.m3u"

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
    # 1. Raw UTF-8 (no compression)
    try:
        return data.decode("utf-8")
    except Exception:
        pass

    # 2. Brotli
    if HAS_BROTLI:
        try:
            return brotli.decompress(data).decode("utf-8")
        except Exception:
            pass

    # 3. Zstandard
    if HAS_ZSTD:
        try:
            return zstd.ZstdDecompressor().decompress(data).decode("utf-8")
        except Exception:
            pass

    # 4. Gzip
    try:
        return zlib.decompress(data, zlib.MAX_WBITS | 16).decode("utf-8")
    except Exception:
        pass

    # 5. Zlib deflate
    try:
        return zlib.decompress(data).decode("utf-8")
    except Exception:
        pass

    # 6. Raw deflate (no header)
    try:
        return zlib.decompress(data, -zlib.MAX_WBITS).decode("utf-8")
    except Exception:
        pass

    return None


def fetch_json(url):
    resp = SESSION.get(url, timeout=15, allow_redirects=True)
    enc = resp.headers.get("content-encoding", "none")
    ct  = resp.headers.get("content-type", "")
    print(f"  [{url}]")
    print(f"    status={resp.status_code} size={len(resp.content)}B encoding={enc!r} content-type={ct!r}")

    if resp.status_code != 200:
        print(f"  ERROR: HTTP {resp.status_code}")
        sys.exit(1)

    raw = resp.content
    if not raw:
        print("  ERROR: Empty response body")
        sys.exit(1)

    # Print first 8 bytes as hex to identify compression magic bytes
    print(f"    First 8 bytes (hex): {raw[:8].hex()}")

    text = try_decompress(raw)
    if text is None:
        print("  ERROR: Could not decompress response with any known method")
        sys.exit(1)

    text = text.strip()
    print(f"    Decoded preview: {text[:80]}")

    try:
        return json.loads(text)
    except Exception as e:
        print(f"  ERROR: JSON decode failed — {e}")
        print(f"  Full text preview:\n{text[:500]}")
        sys.exit(1)


def main():
    print("Fetching channel list ...")
    channels = fetch_json(CHANNELS_URL)
    if not isinstance(channels, list):
        channels = [channels]

    print("Fetching cookie ...")
    cookie_data = fetch_json(COOKIE_URL)
    cookie_str = ""
    for item in cookie_data:
        if "cookie" in item:
            cookie_str = item["cookie"]
            break

    print("Fetching channel status / final URLs ...")
    raw_status = fetch_json(STATUS_URL)

    # Build lookup: channel_id -> final_url
    status_map = {}
    if isinstance(raw_status, list):
        for entry in raw_status:
            cid = str(entry.get("channel_id", ""))
            final_url = entry.get("error_details", {}).get("final_url", "")
            if cid and final_url:
                status_map[cid] = final_url
    elif isinstance(raw_status, dict):
        cid = str(raw_status.get("channel_id", ""))
        final_url = raw_status.get("error_details", {}).get("final_url", "")
        if cid and final_url:
            status_map[cid] = final_url

    print(f"  {len(status_map)} channel(s) have a final_url in the status file.")

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
            f'key-id="{key_id}" '
            f'key="{key}"'
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

    print(f"\nDone! Playlist written to '{OUTPUT_FILE}' with {len(channels)} channel(s).")


if __name__ == "__main__":
    main()
