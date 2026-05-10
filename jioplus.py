import json
import urllib.request
import time

def fetch_data(url):
    """Fetching JSON data...."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return {}

def fetch_key(url):
    """Fetches the raw text/key from the license server using OTT Navigator User-Agent."""
    try:
        headers = {
            'User-Agent': 'OTT Navigator/1.7.4.1 (Linux;Android 11; en; 1tas50z)'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8').strip()
    except Exception as e:
        print(f"Failed to fetch key from {url}: {e}")
        return None

def generate_m3u(playback_dict, meta_list, output_filename="playlist.m3u"):
    meta_dict = {str(item.get("tvg-id", "")): item for item in meta_list}
    
    with open(output_filename, "w", encoding="utf-8") as file:
        file.write("#EXTM3U\n")
        
        for channel_id, stream_info in playback_dict.items():
            if str(channel_id) in meta_dict:
                meta = meta_dict[str(channel_id)]
                tvg_id = meta.get("tvg-id", "")
                
                extinf = (
                    f'#EXTINF:-1 tvg-id="{tvg_id}" '
                    f'group-title="{meta.get("group-title", "")}" '
                    f'tvg-logo="{meta.get("tvg-logo", "")}",'
                    f'{meta.get("channel-name", "")}'
                )
                file.write(extinf + "\n")
                
                kid = stream_info.get("kid", "")
                key_path = stream_info.get("key", "")
                
                actual_key = None
                if kid and key_path:
                    fetch_url = f"{kid}:{key_path}={tvg_id}"
                    print(f"Fetching license key for: {meta.get('channel-name')}...")
                    actual_key = fetch_key(fetch_url)
                    time.sleep(0.5)
                
                raw_stream_url = stream_info.get("url", "")
                if ".mpd" in raw_stream_url:
                    file.write('#KODIPROP:inputstream=inputstream.adaptive\n')
                    file.write('#KODIPROP:inputstream.adaptive.manifest_type=mpd\n')
                    file.write('#KODIPROP:inputstream.adaptive.license_type=com.widevine.alpha\n') 
                    
                    if actual_key:
                        file.write(f'#KODIPROP:inputstream.adaptive.license_key={actual_key}\n')
                
                formatted_stream_url = raw_stream_url.replace("|cookie=", "?")
                file.write(formatted_stream_url + "\n\n")

if __name__ == "__main__":
    channels_url = "https://raw.githubusercontent.com/Anasvirat18/Jio_/refs/heads/main/stream.json"
    metadata_url = "https://raw.githubusercontent.com/qwerty180506/Geo/refs/heads/main/meta.txt"
    
    print("Fetching master files...")
    channels_data = fetch_data(channels_url)
    metadata_data = fetch_data(metadata_url)
    
    if channels_data and metadata_data:
        generate_m3u(channels_data, metadata_data)
        print("\nPlaylist generated successfully as 'playlist.m3u'")
    else:
        print("Failed to retrieve source data.")
