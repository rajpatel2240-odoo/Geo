import json
import os
import urllib.request

def clean_url(url):
    """Converts '...index.mpd|drmScheme=clearkey' — strips that suffix for the base MPD URL."""
    if '|drmScheme=' in url:
        return url.split('|drmScheme=')[0]
    return url

def generate_m3u_from_url(jio_url, output_file):
    print(f"Fetching stream data from {jio_url}...")
    try:
        req = urllib.request.Request(jio_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(f"Error fetching URL: HTTP Status {response.status}")
                return
            raw_data = response.read().decode('utf-8')
            jio_data = json.loads(raw_data)
    except Exception as e:
        print(f"Error fetching or parsing the URL data: {e}")
        return

    # Support both a list of channel objects or a dict keyed by channel id
    if isinstance(jio_data, dict):
        channels = list(jio_data.values())
    elif isinstance(jio_data, list):
        channels = jio_data
    else:
        print("Unexpected JSON structure.")
        return

    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("#EXTM3U\n")

        for channel in channels:
            channel_id = str(channel.get("id", ""))
            mpd_url = channel.get("mpd_url", "")
            license_url = channel.get("license_url", "")

            if not mpd_url:
                continue

            base_url = clean_url(mpd_url)

            name = channel.get("name", "Unknown Channel")
            logo = channel.get("logo", "")
            group = channel.get("group", "Unknown")
            user_agent = channel.get("user_agent", "@cloudplay")

            extinf = (
                f'#EXTINF:-1 tvg-id="{channel_id}" '
                f'tvg-logo="{logo}" '
                f'group-title="{group}",'
                f'{name}\n'
            )

            drm_props = (
                '#KODIPROP:inputstream=inputstream.adaptive\n'
                '#KODIPROP:inputstream.adaptive.manifest_type=mpd\n'
                '#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
                '#KODIPROP:inputstream.adaptive.stream_headers=User-Agent=@cloudplay\n'
                f'#KODIPROP:inputstream.adaptive.license_key={license_url}\n'
            )

            out.write(extinf)
            out.write(drm_props)
            out.write(base_url + "|drmScheme=clearkey")
            out.write("\n\n")

    print(f"Success! M3U playlist generated as '{output_file}'.")

if __name__ == "__main__":
    JIO_URL = "https://noisy-truth-6766.streamstar18.workers.dev/"
    OUTPUT_FILENAME = "jiotv.m3u"

    generate_m3u_from_url(JIO_URL, OUTPUT_FILENAME)
