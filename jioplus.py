# Credits 🙏: cloudplay
# Telegram: https://t.me/cloudply

# Credits 🙏: allinonereborn
# Website: https://allinonereborn-livetv-hub.pages.dev/

from flask import Flask, jsonify, request
import cloudscraper
import requests
import base64
import os
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# =========================
# CONFIG
# =========================

SYNC_SECRET = os.environ.get("SYNC_SECRET", "changeme")
GH_TOKEN = os.environ.get("GH_TOKEN")

REPO = "qwerty180506/Geo"
FILE_PATH = "jioplus.m3u"

CHANNELS_URL = "https://allinonereborn.online/jtv-fetch/jstr4web.json"
COOKIES_URL = "https://allinonereborn.online/jstrweb2/cookies.json"
RESULTS_URL = "https://allinonereborn.online/jtv-fetch/jstarcookie/cookie.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://allinonereborn.online",
    "Origin": "https://allinonereborn.online",
    "Accept-Language": "en-US,en;q=0.9"
}

# =========================
# HELPERS
# =========================

def safe_json_get(scraper, url):

    try:

        response = scraper.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        print(f"\n[FETCH] {url}")
        print(f"[STATUS] {response.status_code}")
        print(f"[TYPE] {content_type}")
        print(f"[PREVIEW] {response.text[:200]}\n")

        if "json" not in content_type:

            print(f"[ERROR] Non JSON response from {url}")

            return None

        return response.json()

    except Exception as e:

        print(f"[ERROR] Failed fetching {url}")
        print(str(e))

        return None


def fetch_missing_key(ch_id):

    api_url = (
        f"https://keys.cloudplay.qzz.io/"
        f"pl/plkey.php?id={ch_id}"
    )

    headers = {
        "User-Agent": (
            "OTT Navigator/1.7.4.1 "
            "(Linux;Android 11; en; 1tas50z)"
        ),
        "Accept": "application/json"
    }

    try:

        response = requests.get(
            api_url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        keys_list = data.get("keys", [])

        if keys_list and isinstance(keys_list, list):

            first_key_pair = keys_list[0]

            key_id = first_key_pair.get("kid")
            key = first_key_pair.get("k")

            if key_id and key:

                return ch_id, key_id, key

    except Exception as e:

        print(f"[KEY ERROR] {ch_id}: {e}")

    return ch_id, None, None


def upload_to_github(content):

    if not GH_TOKEN:

        return False, "GH_TOKEN missing"

    github_api_url = (
        f"https://api.github.com/repos/"
        f"{REPO}/contents/{FILE_PATH}"
    )

    gh_headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Render-IPTV-Updater"
    }

    sha = None

    # Get existing SHA

    try:

        sha_response = requests.get(
            github_api_url,
            headers=gh_headers,
            timeout=20
        )

        if sha_response.status_code == 200:

            sha = sha_response.json().get("sha")

    except Exception as e:

        print(f"[SHA ERROR] {e}")

    encoded_content = base64.b64encode(
        content.encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "Automated IPTV update",
        "content": encoded_content
    }

    if sha:

        payload["sha"] = sha

    try:

        upload_response = requests.put(
            github_api_url,
            json=payload,
            headers=gh_headers,
            timeout=30
        )

        print(
            f"[GITHUB STATUS] "
            f"{upload_response.status_code}"
        )

        if upload_response.status_code in [200, 201]:

            return True, "GitHub upload successful"

        return False, (
            f"GitHub API Error: "
            f"{upload_response.status_code} "
            f"{upload_response.text}"
        )

    except Exception as e:

        return False, f"GitHub upload failed: {e}"


# =========================
# MAIN PIPELINE
# =========================

def run_m3u_pipeline():

    print("\n========== STARTING PIPELINE ==========\n")

    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "mobile": False
        }
    )

    # =========================
    # FETCH DATA
    # =========================

    channels_data = safe_json_get(
        scraper,
        CHANNELS_URL
    )

    cookies_data = safe_json_get(
        scraper,
        COOKIES_URL
    )

    results_data = safe_json_get(
        scraper,
        RESULTS_URL
    )

    if not channels_data:

        return False, "Failed fetching channels"

    if not cookies_data:

        return False, "Failed fetching cookies"

    if not results_data:

        return False, "Failed fetching results"

    # =========================
    # FALLBACK COOKIE
    # =========================

    fallback_cookie = ""

    if isinstance(cookies_data, list):

        for item in cookies_data:

            if (
                isinstance(item, dict)
                and "cookie" in item
            ):

                fallback_cookie = item["cookie"]

                break

    print(f"[COOKIE FOUND] {bool(fallback_cookie)}")

    # =========================
    # STREAM URLS
    # =========================

    specific_urls = {}

    for result in results_data.get(
        "failed_results",
        []
    ):

        try:

            ch_id = str(result.get("channel_id"))

            error_details = result.get(
                "error_details",
                {}
            )

            if "final_url" in error_details:

                specific_urls[ch_id] = (
                    error_details["final_url"]
                )

        except Exception as e:

            print(f"[FAILED RESULT ERROR] {e}")

    for result in results_data.get(
        "successful_results",
        []
    ):

        try:

            ch_id = str(result.get("channel_id"))

            if "final_url" in result:

                specific_urls[ch_id] = (
                    result["final_url"]
                )

        except Exception as e:

            print(f"[SUCCESS RESULT ERROR] {e}")

    print(
        f"[SPECIFIC URLS] "
        f"{len(specific_urls)}"
    )

    # =========================
    # MISSING KEYS
    # =========================

    channels_needing_keys = []

    for channel in channels_data:

        ch_id = str(channel.get("id"))

        key_id = str(
            channel.get("keyId", "")
        ).strip()

        key = str(
            channel.get("key", "")
        ).strip()

        if (
            not key_id
            or not key
            or key_id.lower() == "null"
            or key.lower() == "null"
        ):

            channels_needing_keys.append(ch_id)

    print(
        f"[MISSING KEYS] "
        f"{len(channels_needing_keys)}"
    )

    # =========================
    # FETCH MISSING KEYS
    # =========================

    fetched_keys = {}

    if channels_needing_keys:

        workers = min(
            10,
            len(channels_needing_keys)
        )

        with ThreadPoolExecutor(
            max_workers=workers
        ) as executor:

            results = executor.map(
                fetch_missing_key,
                channels_needing_keys
            )

            for ch_id, kid, k in results:

                if kid and k:

                    fetched_keys[ch_id] = {
                        "keyId": kid,
                        "key": k
                    }

    print(
        f"[FETCHED KEYS] "
        f"{len(fetched_keys)}"
    )

    # =========================
    # BUILD M3U
    # =========================

    m3u_lines = ["#EXTM3U"]

    total_channels = 0

    for channel in channels_data:

        try:

            ch_id = str(channel.get("id"))

            name = channel.get(
                "name",
                "Unknown"
            )

            category = channel.get(
                "category",
                "Live TV"
            )

            logo = channel.get(
                "logo",
                ""
            )

            base_url = channel.get(
                "url",
                ""
            )

            key_id = channel.get("keyId")
            key = channel.get("key")

            # Replace missing keys

            if (
                not key_id
                or not key
                or str(key_id).lower() == "null"
                or str(key).lower() == "null"
            ):

                if ch_id in fetched_keys:

                    key_id = fetched_keys[ch_id][
                        "keyId"
                    ]

                    key = fetched_keys[ch_id][
                        "key"
                    ]

            # Final stream URL

            if ch_id in specific_urls:

                final_stream_url = (
                    specific_urls[ch_id]
                )

            else:

                if not base_url:

                    continue

                separator = (
                    "&"
                    if "?" in base_url
                    else "?"
                )

                if fallback_cookie:

                    final_stream_url = (
                        f"{base_url}"
                        f"{separator}"
                        f"{fallback_cookie}"
                    )

                else:

                    final_stream_url = base_url

            # EXTINF

            extinf = (
                f'#EXTINF:-1 '
                f'tvg-id="{ch_id}" '
                f'tvg-logo="{logo}" '
                f'group-title="{category}",'
                f'{name}'
            )

            m3u_lines.append(extinf)

            # DRM

            if key_id and key:

                if (
                    str(key_id).lower() != "null"
                    and str(key).lower() != "null"
                ):

                    m3u_lines.append(
                        "#KODIPROP:"
                        "inputstream.adaptive."
                        "license_type=clearkey"
                    )

                    m3u_lines.append(
                        "#KODIPROP:"
                        "inputstream.adaptive."
                        f"license_key="
                        f"{key_id}:{key}"
                    )

            # URL

            m3u_lines.append(final_stream_url)

            total_channels += 1

        except Exception as e:

            print(f"[CHANNEL ERROR] {e}")

    print(
        f"[TOTAL CHANNELS] "
        f"{total_channels}"
    )

    # =========================
    # FINAL M3U
    # =========================

    header_text = (
        "# Credits 🙏: cloudplay\n"
        "# Telegram: https://t.me/cloudply\n"
        "# Credits 🙏: allinonereborn\n"
        "# Website: "
        "https://allinonereborn-livetv-hub.pages.dev/\n\n"
    )

    m3u_final_string = (
        header_text
        + "\n".join(m3u_lines)
        + "\n"
    )

    # =========================
    # UPLOAD TO GITHUB
    # =========================

    success, message = upload_to_github(
        m3u_final_string
    )

    print(f"[UPLOAD RESULT] {message}")

    return success, message


# =========================
# ROUTES
# =========================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "status": "online",
        "message": "Server running"
    })


@app.route("/health", methods=["GET"])
def health():

    return "OK", 200


@app.route("/sync", methods=["GET"])
def trigger_sync():

    provided_key = request.args.get("key")

    if provided_key != SYNC_SECRET:

        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        }), 403

    success, message = run_m3u_pipeline()

    if success:

        return jsonify({
            "status": "success",
            "message": message
        }), 200

    return jsonify({
        "status": "error",
        "message": message
    }), 500


# =========================
# START APP
# =========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
