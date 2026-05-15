import cloudscraper
import json

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

    # 1. Fetch main channel details
    try:
        response1 = scraper.get(url1, headers=headers)
        response1.raise_for_status() 
        channels_data = response1.json()
    except Exception as e:
        print(f"Error fetching Link 1: {e}")
        if 'response1' in locals():
            print(f"Server response preview: {response1.text[:250]}")
        return

    # 2. Fetch the fallback cookie
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

    # 3. Fetch the specific final URLs for channels
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

    print("Processing channels and building M3U...")
    
    m3u_lines = ["#EXTM3U"]

    # Loop through the main channels list
    for channel in channels_data:
        ch_id = str(channel.get("id"))
        name = channel.get("name", "Unknown")
        category = channel.get("category", "")
        logo = channel.get("logo", "")
        base_url = channel.get("url", "")
        key_id = channel.get("keyId", "")
        key = channel.get("key", "")

        # Condition 1 & 2
        if ch_id in specific_urls:
            final_stream_url = specific_urls[ch_id]
            
        # Condition 3
        else:
            separator = "&" if "?" in base_url else "?"
            final_stream_url = f"{base_url}{separator}{fallback_cookie}"

        extinf = f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{category}",{name}'
        m3u_lines.append(extinf)
        
        if key_id and key:
            m3u_lines.append('#KODIPROP:inputstream.adaptive.license_type=clearkey')
            m3u_lines.append(f'#KODIPROP:inputstream.adaptive.license_key={key_id}:{key}')
            
        m3u_lines.append(final_stream_url)

    output_filename = "jioplus.m3u"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines))

    print(f"Success! '{output_filename}' has been generated with {len(channels_data)} channels.")

if __name__ == "__main__":
    generate_m3u()
