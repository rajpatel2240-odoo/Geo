import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# ── Config ────────────────────────────────────────────────────────────────────
MAX_WORKERS = 20   # parallel key fetches
TIMEOUT     = 5    # seconds per license request
# ──────────────────────────────────────────────────────────────────────────────

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "@cloudplay"})

key_cache: dict = {}   # license_url -> JSON string or None


def clean_url(url):
    """Strips '|drmScheme=clearkey' suffix to get the bare MPD URL."""
    return url.split("|drmScheme=")[0] if "|drmScheme=" in url else url


def fetch_clearkey(license_url):
    """
    Fetches a ClearKey license URL and returns the raw JSON string, e.g.
      {"keys":[{"kty":"oct","kid":"...","k":"..."}],"type":"temporary"}
    Returns None on any failure. Results are cached so duplicate URLs
    are only fetched once.
    """
    if not license_url:
        return None

    # Cache hit — no network call needed
    if license_url in key_cache:
        return key_cache[license_url]

    try:
        resp = SESSION.get(license_url, timeout=TIMEOUT)
        if resp.status_code != 200:
            print(f"  [WARN] HTTP {resp.status_code} for {license_url}")
            key_cache[license_url] = None
            return None
        raw = resp.text.strip()
        json.loads(raw)          # validate JSON
        key_cache[license_url] = raw
        return raw
    except Exception as e:
        print(f"  [WARN] {license_url}: {e}")
        key_cache[license_url] = None
        return None


def fetch_all_keys(channels):
    """
    Fires all license-key requests in parallel and returns a mapping of
    license_url -> clearkey JSON (or None on failure).
    Duplicate URLs are deduplicated before dispatching.
    """
    unique_urls = {
        ch.get("license_url", "")
        for ch in channels
        if ch.get("license_url") and ch.get("mpd_url")
    }

    results = {}
    done = 0
    total = len(unique_urls)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_to_url = {pool.submit(fetch_clearkey, url): url for url in unique_urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            results[url] = future.result()
            done += 1
            status = "✓" if results[url] else "⚠"
            print(f"  [{done}/{total}] {status} {url[:80]}")

    return results


def generate_m3u_from_url(jio_url, output_file):
    print(f"Fetching channel list from {jio_url}...")
    t0 = time.perf_counter()

    try:
        resp = SESSION.get(jio_url, timeout=15)
        resp.raise_for_status()
        jio_data = resp.json()
    except Exception as e:
        print(f"Error fetching channel list: {e}")
        return

    if isinstance(jio_data, dict):
        channels = list(jio_data.values())
    elif isinstance(jio_data, list):
        channels = jio_data
    else:
        print("Unexpected JSON structure.")
        return

    print(f"Found {len(channels)} channels.\n")
    print(f"Fetching ClearKeys in parallel (workers={MAX_WORKERS}, timeout={TIMEOUT}s)...")

    key_map = fetch_all_keys(channels)

    print(f"\nWriting {output_file}...")
    with open(output_file, "w", encoding="utf-8") as out:
        out.write("#EXTM3U\n")

        for channel in channels:
            mpd_url     = channel.get("mpd_url", "")
            license_url = channel.get("license_url", "")
            if not mpd_url:
                continue

            channel_id = str(channel.get("id", ""))
            name       = channel.get("name", "Unknown Channel")
            logo       = channel.get("logo", "")
            group      = channel.get("group", "Unknown")
            base_url   = clean_url(mpd_url)

            # Use fetched key JSON; fall back to dynamic URL if fetch failed
            license_key_value = key_map.get(license_url) or license_url

            out.write(
                f'#EXTINF:-1 tvg-id="{channel_id}" '
                f'tvg-logo="{logo}" '
                f'group-title="{group}",'
                f'{name}\n'
            )
            out.write(
                '#KODIPROP:inputstream=inputstream.adaptive\n'
                '#KODIPROP:inputstream.adaptive.manifest_type=mpd\n'
                '#KODIPROP:inputstream.adaptive.license_type=clearkey\n'
                '#KODIPROP:inputstream.adaptive.stream_headers=User-Agent=@cloudplay\n'
                f'#KODIPROP:inputstream.adaptive.license_key={license_key_value}\n'
            )
            out.write(base_url + "|drmScheme=clearkey\n\n")

    elapsed = time.perf_counter() - t0
    print(f"\nDone! '{output_file}' written in {elapsed:.1f}s.")


if __name__ == "__main__":
    JIO_URL         = "https://noisy-truth-6766.streamstar18.workers.dev/"
    OUTPUT_FILENAME = "jiotv.m3u"
    generate_m3u_from_url(JIO_URL, OUTPUT_FILENAME)
