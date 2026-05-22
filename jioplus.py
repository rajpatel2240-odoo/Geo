#Credits 🙏: cloudplay
#Telegram: https://t.me/cloudply

#Credits 🙏: allinonereborn
#Website: https://allinonereborn-livetv-hub.pages.dev/

from flask import Flask, jsonify
import cloudscraper
import requests
import json
import base64
import os
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

def fetch_missing_key(ch_id):
    api_url = f"https://qzz.io{ch_id}"
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

def run_m3u_pipeline():
    url1 = "https://allinonereborn.online"
    url2 = "https://allinonereborn.online"
    url3 = "https://allinonereborn.online"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://allinonereborn.online",
        "Origin": "https://allinonereborn.online",
        "Accept-Language": "en-US,en;q=0.9"
    }

    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','mobile': False})

    try:
        channels_data = scraper.get(url1, headers=headers).json()
        cookies_data = scraper.get(url2, headers=headers).json()
        url3_data = scraper.get(url3, headers=headers).json()
    except Exception as e:
        return f"Scraping failed: {str(e)}"

    fallback_cookie = ""
    for item in cookies_data:
        if "cookie" in item:
            fallback_cookie = item["cookie"]
            break

    specific_urls = {}
    for result in url3_data.get("failed_results", []):
        ch_id = str(result.get("channel_id"))
        if "error_details" in result and "final_url" in result["error_details"]:
            specific_urls[ch_id] = result["error_details"]["final_url"]
    for result in url3_data.get("successful_results", []):
        ch_id = str(result.get("channel_id"))
        if "final_url" in result:
            specific_urls[ch_id] = result["final_url"]

    channels_needing_keys = []
    for channel in channels_data:
        ch_id = str(channel.get("id"))
        key_id = str(channel.get("keyId", "")).strip()
        key = str(channel.get("key", "")).strip()
        if not key_id or not key or key_id.lower() == "null" or key.lower() == "null":
            channels_needing_keys.append(ch_id)

    fetched_keys = {}
    if channels_needing_keys:
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(fetch_missing_key, channels_needing_keys)
            for ch_id, kid, k in results:
                if kid and k:
                    fetched_keys[ch_id] = {"keyId": kid, "key": k}

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

    header_text = "#Credits 🙏: cloudplay\n#Telegram: https://t.me\n#Credits 🙏: allinonereborn\n#Website: https://pages.dev\n\n"
    m3u_final_string = header_text + "\n".join(m3u_lines) + "\n"

    # --- GITHUB API UPLOAD ---
    github_token = os.environ.get("GH_TOKEN") 
    repo = "qwerty180506/Geo"
    file_path = "jioplus.m3u"
    gh_url = f"https://github.com{repo}/contents/{file_path}"
    
    gh_headers = {
        "Authorization": f"Bearer {github_token}",
        "User-Agent": "Render-App"
    }

    sha = None
    try:
        sha_res = requests.get(gh_url, headers=gh_headers)
        if sha_res.status_code == 200:
            sha = sha_res.json().get("sha")
    except Exception:
        pass

    encoded_content = base64.b64encode(m3u_final_string.encode('utf-8')).decode('utf-8')
    payload = {"message": "Automated IPTV M3U update", "content": encoded_content}
    if sha:
        payload["sha"] = sha

    try:
        upload_res = requests.put(gh_url, json=payload, headers=gh_headers)
        if upload_res.status_code in [200, 201]:
            return "Success"
        else:
            return f"GitHub API Error: {upload_res.status_code}"
    except Exception as e:
        return f"GitHub Push Failed: {str(e)}"

@app.route('/')
def home():
    return "IPTV Sync Server is Running"

@app.route('/sync')
def trigger_sync():
    result = run_m3u_pipeline()
    if result == "Success":
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error", "message": result}), 500

if __name__ == "__main__":
    # Render binds to the PORT environment variable automatically
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
