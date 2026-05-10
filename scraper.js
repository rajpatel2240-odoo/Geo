const axios = require("axios");
const fs = require("fs");

const STREAM_JSON_URL = "https://jo-json.vodep39240327.workers.dev";
const OUTPUT_FILE = "stream.json";

async function fetchAndSaveJson() {
  try {
    const response = await axios.get(STREAM_JSON_URL);
    const data = response.data;

    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(data, null, 2), "utf-8");
    console.log("✅ stream.json saved successfully.");
  } catch (error) {
    console.error("❌ Failed to fetch JSON:", error.message);
    process.exit(1);
  }
}

fetchAndSaveJson();
