import jiotvWorker from "./jiotv.js";
import { generateFancodeM3U } from "./fancode.js";

// ---------------- BASE64 ---------------- //

function toBase64(str) {
  const bytes =
    new TextEncoder().encode(str);

  let binary = "";

  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(
      bytes[i]
    );
  }

  return btoa(binary);
}

// ---------------- GITHUB UPLOAD ---------------- //

async function uploadToGitHub(
  content,
  env,
  filename
) {

  const api =
    `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/contents/${filename}`;

  let sha;

  // GET OLD FILE
  const oldFile = await fetch(api, {
    headers: {
      Authorization:
        `Bearer ${env.GITHUB_TOKEN}`,
      "User-Agent":
        "Cloudflare-Worker",
    },
  });

  try {
    const oldData =
      await oldFile.json();

    sha = oldData.sha;
  } catch {}

  // UPLOAD NEW FILE
  const upload = await fetch(api, {
    method: "PUT",

    headers: {
      Authorization:
        `Bearer ${env.GITHUB_TOKEN}`,
      "Content-Type":
        "application/json",
      "User-Agent":
        "Cloudflare-Worker",
    },

    body: JSON.stringify({
      message:
        `Auto update ${filename}`,

      content:
        toBase64(content),

      sha,
    }),
  });

  console.log(
    `${filename}: ${upload.status}`
  );
}

// ---------------- MAIN ---------------- //

export default {

  // CRON
  async scheduled(event, env, ctx) {

    console.log("Cron started");

    try {

      // ---------------- JIOTV ---------------- //

      const jiotvResponse =
        await jiotvWorker.fetch(
          new Request(
            "https://dummy.url"
          ),
          env,
          ctx
        );

      const jiotvM3U =
        await jiotvResponse.text();

      await uploadToGitHub(
        jiotvM3U,
        env,
        "jiotv_cf.m3u"
      );

      console.log(
        "JioTV updated"
      );

      // ---------------- FANCODE ---------------- //

      const fancodeM3U =
        await generateFancodeM3U();

      await uploadToGitHub(
        fancodeM3U,
        env,
        "fancode_1080p.m3u"
      );

      console.log(
        "Fancode updated"
      );

    } catch (e) {

      console.log(
        "Cron error:",
        e.toString()
      );
    }
  },

  // MANUAL TEST
  async fetch(request, env, ctx) {

    await this.scheduled(
      null,
      env,
      ctx
    );

    return new Response(
      "All playlists updated"
    );
  },
};
