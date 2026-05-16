import cloudscraper
import requests
import json
from concurrent.futures import ThreadPoolExecutor

def fetch_missing_key(ch_id):
    """
    Fetches missing clearkeys from the cloudplay API for a specific channel ID
    using the requested OTT Navigator User-Agent.
    """
    api_url = f"https://keys.cloudplay.qzz.io/pl/plkey.php?id={ch_id}"
    headers = {
        "User-Agent": "OTT Navigator/1.7.4.1 (Linux;Android 11; en; 1tas50z)",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            keys_list = data.get("keys", [])
            if keys_list and isinstance(keys_list, list):
                first_key_pair = keys_list[0]
                key_id = first_key_pair.get("kid")
                key = first_key_pair.get("k")
                
                if key_id and key:
                    return ch_id, key_id, key
    except Exception:
        pass
    return ch_id, None, None

def generate_m3u():
    url1 = "https://allinonereborn.online/jtv-fetch/jstr4web.json"
    url2 = "https://allinonereborn.online/jstrweb2/cookies.json"
    url3 = "https://allinonereborn.online/jtv-fetch/jstarcookie/cookie.json"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://allinonereborn.online/",
        "Origin": "https://allinonereborn.online",
        "Accept-Language": "en-US,en;q=0.9"
    }

    print("Initializing Cloudscraper session...")
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )

    print("Fetching data from the URLs...")

    try:
        response1 = scraper.get(url1, headers=headers)
        response1.raise_for_status() 
        channels_data = response1.json()
    except Exception as e:
        print(f"Error fetching Link 1: {e}")
        if 'response1' in locals():
            print(f"Server response preview: {response1.text[:250]}")
        return

    try:
        response2 = scraper.get(url2, headers=headers)
        response2.raise_for_status()
        cookies_data = response2.json()
        fallback_cookie = ""
        
        for item in cookies_data:
            if "cookie" in item:
                fallback_cookie = item["cookie"]
                break
    except Exception as e:
        print(f"Error fetching Link 2: {e}")
        return

    specific_urls = {}
    try:
        response3 = scraper.get(url3, headers=headers)
        response3.raise_for_status()
        url3_data = response3.json()
        
        for result in url3_data.get("failed_results", []):
            ch_id = str(result.get("channel_id"))
            if "error_details" in result and "final_url" in result["error_details"]:
                specific_urls[ch_id] = result["error_details"]["final_url"]
                
        for result in url3_data.get("successful_results", []):
            ch_id = str(result.get("channel_id"))
            if "final_url" in result:
                specific_urls[ch_id] = result["final_url"]
                
    except Exception as e:
        print(f"Error fetching Link 3: {e}")
        return

    channels_needing_keys = []
    for channel in channels_data:
        ch_id = str(channel.get("id"))
        key_id = str(channel.get("keyId", "")).strip()
        key = str(channel.get("key", "")).strip()
        
        if not key_id or not key or key_id.lower() == "null" or key.lower() == "null":
            channels_needing_keys.append(ch_id)

    fetched_keys = {}
    if channels_needing_keys:
        print(f"Found {len(channels_needing_keys)} channels missing keys. Fetching from cloudplay API using 10 workers...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(fetch_missing_key, channels_needing_keys)
            for ch_id, kid, k in results:
                if kid and k:
                    fetched_keys[ch_id] = {"keyId": kid, "key": k}

    print("Processing channels and building M3U...")
    
    m3u_lines = ["#EXTM3U"]

    for channel in channels_data:
        ch_id = str(channel.get("id"))
        name = channel.get("name", "Unknown")
        category = channel.get("category", "")
        logo = channel.get("logo", "")
        base_url = channel.get("url", "")
        
        key_id = channel.get("keyId")
        key = channel.get("key")
        
        k_id_str = str(key_id).strip().lower() if key_id else "null"
        k_str = str(key).strip().lower() if key else "null"

        if k_id_str == "null" or k_str == "null":
            if ch_id in fetched_keys:
                key_id = fetched_keys[ch_id]["keyId"]
                key = fetched_keys[ch_id]["key"]
                k_id_str, k_str = "valid", "valid"

        if ch_id in specific_urls:
            final_stream_url = specific_urls[ch_id]
        else:
            separator = "&" if "?" in base_url else "?"
            final_stream_url = f"{base_url}{separator}{fallback_cookie}"

        extinf = f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{category}",{name}'
        m3u_lines.append(extinf)
        
        if key_id and key and k_id_str != "null" and k_str != "null":
            m3u_lines.append('#KODIPROP:inputstream.adaptive.license_type=clearkey')
            m3u_lines.append(f'#KODIPROP:inputstream.adaptive.license_key={key_id}:{key}')
            
        m3u_lines.append(final_stream_url)

    output_filename = "jioplus.m3u"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines) + "\n")

    print(f"Success! '{output_filename}' has been generated with {len(channels_data)} channels.")

if __name__ == "__main__":
    generate_m3u()
