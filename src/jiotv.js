const JSON_URL =
  "https://noisy-truth-6766.streamstar18.workers.dev/";

const HEADERS = {
  "User-Agent":
    "OTT Navigator/1.7.4.1 (Linux;Android 11)",
};

// ---------------- BASE64 SAFE ----------------
function toBase64(str) {
  const bytes = new TextEncoder().encode(str);

  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }

  return btoa(binary);
}

// ---------------- PROCESS CHANNEL (NO FETCH INSIDE) ----------------
async function processChannel(channel) {
  const name = channel.name || "Unknown";
  const chanId = channel.id || "";
  const logo = channel.logo || "";
  const group = channel.group || "Other";

  const mpd = (channel.mpd_url || "").replace(
    "|drmScheme=clearkey",
    ""
  );

  const licenseUrl = channel.license_url || ""; // 👈 DIRECT USE
  const cookie = channel.headers?.cookie || "";

  const finalUrl = cookie ? `${mpd}?${cookie}` : mpd;

  const out = [
    `#EXTINF:-1 tvg-id="${chanId}" tvg-name="${name}" tvg-logo="${logo}" group-title="${group}",${name}`,
  ];

  // ---------------- CLEARKEY NOW DIRECT FROM JSON ----------------
  if (licenseUrl && licenseUrl !== "null") {
    out.push("#KODIPROP:inputstream.adaptive.license_type=clearkey");
    out.push(`#KODIPROP:inputstream.adaptive.license_key=${licenseUrl}`);
  }

  out.push(finalUrl);

  return out.join("\n");
}

// ---------------- SEQUENTIAL GENERATION (SAFE) ----------------
async function generateM3U() {
  const response = await fetch(JSON_URL, {
    headers: HEADERS,
  });

  const channels = await response.json();

  let results = [];

  for (const channel of channels) {
    try {
      const line = await processChannel(channel);
      results.push(line);
    } catch (e) {
      console.log("Channel error:", e.toString());
    }
  }

  return [
    "#EXTM3U",
    "#Credits 🙏: cloudplay",
    "#Telegram: https://t.me/cloudply",
    "",
    ...results,
  ].join("\n\n");
}

// ---------------- GITHUB UPLOAD ----------------
async function uploadToGitHub(content, env) {
  const path = "jiotv.m3u";

  const api = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/contents/${path}`;

  let sha = undefined;

  try {
    const oldFile = await fetch(api, {
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        "User-Agent": "Cloudflare Worker",
      },
    });

    if (oldFile.ok) {
      const data = await oldFile.json();
      sha = data.sha;
    }
  } catch (e) {
    console.log("SHA error:", e.toString());
  }

  const upload = await fetch(api, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: "Auto update playlist",
      content: toBase64(content),
      sha,
    }),
  });

  console.log("UPLOAD STATUS:", upload.status);
  console.log("UPLOAD RESPONSE:", await upload.text());
}

// ---------------- WORKER ENTRY ----------------
export default {
  async scheduled(event, env, ctx) {
    try {
      const m3u = await generateM3U();
      await uploadToGitHub(m3u, env);
      console.log("Cron success");
    } catch (e) {
      console.log("Cron error:", e.toString());
    }
  },

  async fetch(request, env) {
    try {
      const m3u = await generateM3U();
      await uploadToGitHub(m3u, env);

      return new Response("GitHub Updated Successfully");
    } catch (e) {
      return new Response("Error: " + e.toString(), {
        status: 500,
      });
    }
  },
};
