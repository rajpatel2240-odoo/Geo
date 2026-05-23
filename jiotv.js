const JSON_URL = "https://noisy-truth-6766.streamstar18.workers.dev/";

const HEADERS = {
  "User-Agent":
    "OTT Navigator/1.7.4.1 (Linux;Android 11)",
};

const CONCURRENT_REQUESTS = 30;

async function fetchKey(url) {
  try {
    const res = await fetch(url, {
      headers: HEADERS,
    });

    if (res.ok) {
      return (await res.text()).trim();
    }
  } catch {}

  return "";
}

async function processChannel(channel) {
  const name = channel.name || "Unknown";

  const chanId = channel.id || "";

  const logo = channel.logo || "";

  const group = channel.group || "Other";

  const mpd = (channel.mpd_url || "")
    .replace("|drmScheme=clearkey", "");

  const licenseUrl =
    channel.license_url || "";

  const cookie =
    channel.headers?.cookie || "";

  const finalUrl = cookie
    ? `${mpd}?${cookie}`
    : mpd;

  let key = "";

  if (
    licenseUrl &&
    licenseUrl !== "null"
  ) {
    key = await fetchKey(licenseUrl);
  }

  const out = [
    `#EXTINF:-1 tvg-id="${chanId}" tvg-name="${name}" tvg-logo="${logo}" group-title="${group}",${name}`,
  ];

  if (key) {
    out.push(
      "#KODIPROP:inputstream.adaptive.license_type=clearkey"
    );

    out.push(
      `#KODIPROP:inputstream.adaptive.license_key=${key}`
    );
  }

  out.push(finalUrl);

  return out.join("\n");
}

async function runConcurrent(
  tasks,
  limit
) {
  const results = [];

  let index = 0;

  async function worker() {
    while (index < tasks.length) {
      const current = index++;

      results[current] =
        await tasks[current]();
    }
  }

  await Promise.all(
    Array.from(
      { length: limit },
      () => worker()
    )
  );

  return results;
}

async function uploadToGitHub(
  content,
  env
) {
  const path = "jiotv.m3u";

  const api =
    `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/contents/${path}`;

  // Get existing SHA
  let sha = undefined;

  try {
    const oldFile = await fetch(api, {
      headers: {
        Authorization:
          `Bearer ${env.GITHUB_TOKEN}`,
      },
    });

    if (oldFile.ok) {
      const data =
        await oldFile.json();

      sha = data.sha;
    }
  } catch {}

  // Upload new file
  await fetch(api, {
    method: "PUT",

    headers: {
      Authorization:
        `Bearer ${env.GITHUB_TOKEN}`,
      "Content-Type":
        "application/json",
    },

    body: JSON.stringify({
      message:
        "Auto update playlist",
      content: btoa(content),
      sha,
    }),
  });
}

async function generateM3U() {
  const response = await fetch(
    JSON_URL
  );

  const channels =
    await response.json();

  const tasks = channels.map(
    (channel) => () =>
      processChannel(channel)
  );

  const results =
    await runConcurrent(
      tasks,
      CONCURRENT_REQUESTS
    );

  return [
    "#EXTM3U",
    "#Credits 🙏: cloudplay",
    "",
    ...results,
  ].join("\n\n");
}

export default {
  async scheduled(
    event,
    env,
    ctx
  ) {
    const m3u =
      await generateM3U();

    await uploadToGitHub(
      m3u,
      env
    );
  },

  async fetch() {
    return new Response(
      "Worker running"
    );
  },
};
