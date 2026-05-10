import json
import urllib.request
import concurrent.futures
import time

def fetch_data(url):
    """Fetches JSON data...."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return {}

def fetch_single_key(channel_info):
    """Worker function to fetch a single key."""
    channel_name = channel_info['name']
    fetch_url = channel_info['url']
    tvg_id = channel_info['id']
    
    try:
        headers = {'User-Agent': 'OTT Navigator/1.7.4.1 (Linux;Android 11; en; 1tas50z)'}
        req = urllib.request.Request(fetch_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            key = response.read().decode('utf-8').strip()
            print(f"[SUCCESS] Fetched key for: {channel_name}")
            return (tvg_id, key)
    except Exception as e:
        print(f"[FAILED] Could not fetch key for {channel_name}: {e}")
        return (tvg_id, None)

def generate_m3u(playback_dict, meta_list, output_filename="jioplus.m3u"):
    meta_dict = {str(item.get("tvg-id", "")): item for item in meta_list}
    
    fetch_tasks = []
    for channel_id, stream_info in playback_dict.items():
        if str(channel_id) in meta_dict:
            meta = meta_dict[str(channel_id)]
            kid = stream_info.get("kid", "")
            key_path = stream_info.get("key", "")
            
            if kid and key_path:
                fetch_url = f"{kid}:{key_path}={channel_id}"
                fetch_tasks.append({
                    'id': str(channel_id),
                    'name': meta.get('channel-name', 'Unknown'),
                    'url': fetch_url
                })

    fetched_keys = {}
    print(f"Starting concurrent fetch for {len(fetch_tasks)} DRM keys...")
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(fetch_single_key, fetch_tasks)
        
        for tvg_id, key in results:
            if key:
                fetched_keys[tvg_id] = key

    print(f"Finished fetching keys in {round(time.time() - start_time, 2)} seconds.")

    print("Writing jioplus.m3u file...")
    with open(output_filename, "w", encoding="utf-8") as file:
        file.write("#EXTM3U\n")
        
        for channel_id, stream_info in playback_dict.items():
            str_id = str(channel_id)
            if str_id in meta_dict:
                meta = meta_dict[str_id]
                tvg_id = meta.get("tvg-id", "")
                
                extinf = (
                    f'#EXTINF:-1 tvg-id="{tvg_id}" '
                    f'group-title="{meta.get("group-title", "")}" '
                    f'tvg-logo="{meta.get("tvg-logo", "")}",'
                    f'{meta.get("channel-name", "")}'
                )
                file.write(extinf + "\n")
                
                raw_stream_url = stream_info.get("url", "")
                if ".mpd" in raw_stream_url:
                    file.write('#KODIPROP:inputstream=inputstream.adaptive\n')
                    file.write('#KODIPROP:inputstream.adaptive.manifest_type=mpd\n')
                    file.write('#KODIPROP:inputstream.adaptive.license_type=clearkey\n') 
                    
                    actual_key = fetched_keys.get(str_id)
                    if actual_key:
                        file.write(f'#KODIPROP:inputstream.adaptive.license_key={actual_key}\n')
                
                formatted_stream_url = raw_stream_url.replace("|cookie=", "?")
                file.write(formatted_stream_url + "\n\n")

if __name__ == "__main__":
    channels_url = "https://raw.githubusercontent.com/Anasvirat18/Jio_/refs/heads/main/stream.json"
    metadata_url = "https://raw.githubusercontent.com/qwerty180506/Geo/refs/heads/main/meta.txt"
    
    print("Fetching master JSON files...")
    channels_data = fetch_data(channels_url)
    metadata_data = fetch_data(metadata_url)
    
    if channels_data and metadata_data:
        generate_m3u(channels_data, metadata_data)
        print("\nPlaylist generated successfully!")
    else:
        print("Failed to retrieve source data.")
