import requests
import json

# --- Source URLs ---
CHANNELS_URL = "https://allinonereborn.online/jtv-fetch/jstr4web.json"
COOKIE_URL   = "https://allinonereborn.online/jstrweb2/cookies.json"
STATUS_URL   = "https://allinonereborn.online/jtv-fetch/jstarcookie/cookie.json"

OUTPUT_FILE  = "playlist.m3u"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
}

def fetch_json(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main():
    print("Fetching channel list ...")
    channels = fetch_json(CHANNELS_URL)

    print("Fetching cookie ...")
    cookie_data = fetch_json(COOKIE_URL)
    # cookie_data is a list; second item holds the cookie string
    cookie_str = ""
    for item in cookie_data:
        if "cookie" in item:
            cookie_str = item["cookie"]
            break

    print("Fetching channel status / final URLs ...")
    raw_status = fetch_json(STATUS_URL)

    # Build a lookup: channel_id -> final_url (only when status != "failed" or final_url exists)
    # We keep the final_url regardless of status so the caller decides what to do
    status_map = {}
    if isinstance(raw_status, list):
        for entry in raw_status:
            cid = str(entry.get("channel_id", ""))
            final_url = entry.get("error_details", {}).get("final_url", "")
            if cid and final_url:
                status_map[cid] = final_url
    elif isinstance(raw_status, dict):
        # Single-channel response (as shown in the example)
        cid = str(raw_status.get("channel_id", ""))
        final_url = raw_status.get("error_details", {}).get("final_url", "")
        if cid and final_url:
            status_map[cid] = final_url

    print(f"  {len(status_map)} channel(s) have a final_url in the status file.")

    # --- Build M3U ---
    lines = ["#EXTM3U\n"]

    for ch in channels:
        ch_id       = str(ch.get("id", ""))
        name        = ch.get("name", "Unknown")
        category    = ch.get("category", "")
        logo        = ch.get("logo", "")
        base_url    = ch.get("url", "")
        key_id      = ch.get("keyId", "")
        key         = ch.get("key", "")

        # Decide stream URL
        if ch_id in status_map:
            stream_url = status_map[ch_id]          # use the pre-cooked final_url
        else:
            stream_url = f"{base_url}?{cookie_str}" # append cookie as query string

        # #EXTINF line with extended metadata
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

        # DRM key hint as a separate tag (widely supported by players like TiviMate, Kodi)
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
