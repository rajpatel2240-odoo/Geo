import json
import requests
from concurrent.futures import ThreadPoolExecutor

JSON_URL = "https://noisy-truth-6766.streamstar18.workers.dev/"

LICENSE_USER_AGENT = "OTT Navigator/1.7.4.1 (Linux;Android 11; en; 1tas50z)"

def process_channel(channel):
    name = channel.get("name", "Unknown Channel")
    chan_id = channel.get("id", "")
    logo = channel.get("logo", "")
    group = channel.get("group", "Uncategorized")
    raw_mpd = channel.get("mpd_url", "")
    license_url = channel.get("license_url", "")
    cookie = channel.get("headers", {}).get("cookie", "")
    user_agent = channel.get("user_agent", "")

    clean_mpd = raw_mpd.replace("|drmScheme=clearkey", "")

    final_url = f"{clean_mpd}?{cookie}" if cookie else clean_mpd

    key = ""
    if license_url and license_url != "null":
        try:
            headers = {"User-Agent": LICENSE_USER_AGENT}
            response = requests.get(license_url, headers=headers, timeout=10)
            if response.status_code == 200:
                key = response.text.strip()
        except requests.RequestException as e:
            print(f"Failed to fetch key for {name}: {e}")

    m3u_lines = ["Credits 🙏: cloudplay\n"]
    m3u_lines.append("Telegram: https://t.me/cloudply")
    
    m3u_lines.append(f'#EXTINF:-1 tvg-id="{chan_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}')
    
    if key:
        m3u_lines.append('#KODIPROP:inputstream.adaptive.license_type=clearkey')
        m3u_lines.append(f'#KODIPROP:inputstream.adaptive.license_key={key}')
        
    m3u_lines.append(final_url)
    
    return "\n".join(m3u_lines)

def generate_m3u(output_m3u_path, max_workers=15):
    print(f"Fetching JSON data from: {JSON_URL}")
    
    try:
        response = requests.get(JSON_URL, timeout=15)
        response.raise_for_status()
        channels = response.json()
    except requests.RequestException as e:
        print(f"Error fetching JSON from URL: {e}")
        return
    except json.JSONDecodeError:
        print("Error: The URL did not return valid JSON.")
        return

    if not isinstance(channels, list):
        print("Error: Expected a JSON array of channels.")
        return

    print(f"Successfully loaded {len(channels)} channels.")
    print(f"Fetching DRM keys using {max_workers} concurrent workers. This may take a moment...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_channel, channels))

    with open(output_m3u_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for result in results:
            f.write(result + "\n\n")
            
    print(f"\nSuccess! M3U playlist saved to '{output_m3u_path}'.")

if __name__ == "__main__":
    output_file = "jiotv.m3u"
    
    generate_m3u(output_file, max_workers=15)
