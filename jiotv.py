import requests
import json
import sys

# --- Source URLs ---
CHANNELS_URL = "https://allinonereborn.online/jtv-fetch/jstr4web.json"
COOKIE_URL   = "https://allinonereborn.online/jstrweb2/cookies.json"
STATUS_URL   = "https://allinonereborn.online/jtv-fetch/jstarcookie/cookie.json"

OUTPUT_FILE  = "playlist.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://allinonereborn.online/",
    "Origin": "https://allinonereborn.online",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def fetch_json(url):
    resp = SESSION.get(url, timeout=15, allow_redirects=True)
    print(f"  [{url}] status={resp.status_code} content-length={len(resp.content)} bytes")
    if resp.status_code != 200:
        print(f"  ERROR: HTTP {resp.status_code}")
        print(f"  Body preview: {resp.text[:300]}")
        sys.exit(1)
    if not resp.content:
        print(f"  ERROR: Empty response body from {url}")
        sys.exit(1)
    try:
        return resp.json()
    except Exception as e:
        print(f"  ERROR: JSON decode failed — {e}")
        print(f"  Body preview: {resp.text[:500]}")
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

    # Build a lookup: channel_id -> final_url
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
            lines.append(f"#KODIPROP:inputstream.adaptive.license_type=clearkey\n")
            lines.append(f'#KODIPROP:inputstream.adaptive.license_key={{"keys":[{{"kty":"oct","k":"{key}","kid":"{key_id}"}}],"type":"temporary"}}\n')
        lines.append(stream_url + "\n")
        lines.append("\n")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"\nDone! Playlist written to '{OUTPUT_FILE}' with {len(channels)} channel(s).")


if __name__ == "__main__":
    main()
