const JSON_URL = "https://noisy-truth-6766.streamstar18.workers.dev/";

const HEADERS = {
  "User-Agent":
    "OTT Navigator/1.7.4.1 (Linux;Android 11)",
};

const CONCURRENT_REQUESTS = 20;

//
// ---------------- BASE64 (FIXED - NO STACK OVERFLOW) ----------------
//
function toBase64(str) {
  const bytes = new TextEncoder().encode(str);

  let binary = "";
  const len = bytes.length;

  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }

  return btoa(binary);
}

//
// ---------------- FETCH KEY ----------------
//
async function fetchKey(url) {
  try {
    const res = await fetch(url, {
      headers: HEADERS,
    });

    if (res.ok) {
      return (await res.text()).trim();
    }
  } catch (e) {
    console.log("Key fetch failed:", e.toString());
  }

  return "";
}

//
// ---------------- PROCESS CHANNEL ----------------
//
async function processChannel(channel) {
  const name = channel.name || "Unknown";
  const chanId = channel.id || "";
  const logo = channel.logo || "";
  const group = channel.group || "Other";

  const mpd = (channel.mpd_url || "").replace(
    "|drmScheme=clearkey",
    ""
  );

  const licenseUrl = channel.license_url || "";
  const cookie = channel.headers?.cookie || "";

  const finalUrl = cookie ? `${mpd}?${cookie}` : mpd;

  let key = "";

  if (licenseUrl && licenseUrl !== "null") {
    key = await fetchKey(licenseUrl);
  }

  const out = [
    `#EXTINF:-1 tvg-id="${chanId}" tvg-name="${name}" tvg-logo="${logo}" group-title="${group}",${name}`,
  ];

  if (key) {
    out.push("#KODIPROP:inputstream.adaptive.license_type=clearkey");
    out.push(`#KODIPROP:inputstream.adaptive.license_key=${key}`);
  }

  out.push(finalUrl);

  return out.join("\n");
}

//
// ---------------- CONCURRENT RUNNER ----------------
//
async function runConcurrent(tasks, limit) {
  const results = new Array(tasks.length);
  let index = 0;

  async function worker() {
    while (index < tasks.length) {
      const current = index++;

      try {
        results[current] = await tasks[current]();
      } catch (e) {
        console.log("Worker error:", e.toString());
        results[current] = "";
      }
    }
  }

  await Promise.all(
    Array.from({ length: limit }, () => worker())
  );

  return results;
}

//
// ---------------- GENERATE M3U ----------------
//
async function generateM3U() {
  const response = await fetch(JSON_URL, {
    headers: HEADERS,
  });

  const channels = await response.json();

  const tasks = channels.map(
    (channel) => () => processChannel(channel)
  );

  const results = await runConcurrent(
    tasks,
    CONCURRENT_REQUESTS
  );

  return [
    "#EXTM3U",
    "#Credits 🙏: cloudplay",
    "#Telegram: https://t.me/cloudply",
    "",
    ...results.filter(Boolean),
  ].join("\n\n");
}

//
// ---------------- GITHUB UPLOAD ----------------
//
async function uploadToGitHub(content, env) {
  const path = "jiotv.m3u";

  const api = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/contents/${path}`;

  console.log("Uploading to GitHub...");

  let sha = undefined;

  // GET EXISTING FILE
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
    console.log("SHA fetch error:", e.toString());
  }

  // UPLOAD
  const upload = await fetch(api, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "Content-Type": "application/json",
      "User-Agent": "Cloudflare Worker",
    },
    body: JSON.stringify({
      message: "Auto update playlist",
      content: toBase64(content),
      sha,
    }),
  });

  const text = await upload.text();

  console.log("UPLOAD STATUS:", upload.status);
  console.log("UPLOAD RESPONSE:", text);
}

//
// ---------------- WORKER ENTRY ----------------
//
export default {
  // CRON
  async scheduled(event, env, ctx) {
    try {
      const m3u = await generateM3U();
      await uploadToGitHub(m3u, env);
      console.log("Cron completed");
    } catch (e) {
      console.log("Cron error:", e.toString());
    }
  },

  // MANUAL TEST URL
  async fetch(request, env) {
    try {
      const m3u = await generateM3U();
      await uploadToGitHub(m3u, env);

      return new Response("GitHub Updated Successfully", {
        status: 200,
      });
    } catch (e) {
      return new Response(`Error: ${e.toString()}`, {
        status: 500,
      });
    }
  },
};
