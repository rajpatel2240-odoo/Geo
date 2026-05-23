const FANCODE_URL = "https://raw.githubusercontent.com/drmlive/fancode-live-events/refs/heads/main/fancode.json";

const HEADERS = {
  "User-Agent": "Cloudflare-Worker",
};

export async function generateFancodeM3U() {
  const res = await fetch(FANCODE_URL, {
    headers: HEADERS,
  });

  if (!res.ok) {
    throw new Error("Failed to fetch Fancode JSON");
  }

  const data = await res.json();

  let m3u = "#EXTM3U\n";
  m3u += "# Fancode Playlist\n\n";

  for (const match of data.matches || []) {
    if ((match.status || "").toUpperCase() !== "LIVE") {
      continue;
    }

    const stream = match.adfree_url || match.dai_url;

    if (!stream) continue;

    const title =
      (match.event_category || "Unknown") +
      " | " +
      (match.title ||
        match.match_name ||
        "Match");

    const logo = match.src || "";

    m3u += `#EXTINF:-1 tvg-logo="${logo}" group-title="Fancode",${title}\n`;
    m3u += `${stream}\n\n`;
  }

  return m3u;
}
