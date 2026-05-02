import requests

def generate_fancode_m3u():
    url = "https://raw.githubusercontent.com/drmlive/fancode-live-events/refs/heads/main/fancode.json"

    try:
        print(f"Fetching data from {url} ...")
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        print(f"Last updated: {data.get('last update time', 'N/A')}")

        m3u_content = "#EXTM3U\n"
        m3u_content += f"# Source: {url}\n"
        m3u_content += f"# Last Updated: {data.get('last update time', 'N/A')}\n\n"

        added = 0
        skipped = 0

        for match in data.get("matches", []):
            # Only include LIVE matches
            if match.get("status", "").upper() != "LIVE":
                skipped += 1
                continue

            # Prefer adfree_url, fallback to dai_url
            stream_url = match.get("adfree_url") or match.get("dai_url")

            if not stream_url:
                print(f"  [SKIP - no stream] {match.get('match_name', 'Unknown')}")
                skipped += 1
                continue

            category = match.get("event_category", "Unknown")
            title = match.get("title", match.get("match_name", "Unknown"))
            logo = match.get("src", "")

            channel_name = f"{category} | {title}"

            m3u_content += f'#EXTINF:-1 tvg-logo="{logo}" group-title="Fancode",{channel_name}\n'
            m3u_content += f"{stream_url}\n\n"
            added += 1
            print(f"  [LIVE] {channel_name}")

        output_file = "fancode.m3u"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(m3u_content)

        print(f"\n✅ Done! {added} live stream(s) written to '{output_file}'. ({skipped} skipped)")

        if added == 0:
            print("⚠️  No live streams found. All matches may be upcoming or have no stream URL.")

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise

if __name__ == "__main__":
    generate_fancode_m3u()
