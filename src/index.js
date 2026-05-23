import { runJioTV } from "./jiotv.js";
import { runFancode } from "./fancode.js";

export default {
  // ---------------- CRON JOB ----------------
  async scheduled(event, env, ctx) {
    try {
      await Promise.all([
        runJioTV(env),
        runFancode(env),
      ]);

      console.log(
        "Both playlists updated successfully"
      );
    } catch (e) {
      console.log("Cron Error:", e.toString());
    }
  },

  // ---------------- MANUAL URL TRIGGER ----------------
  async fetch(request, env) {
    try {
      await Promise.all([
        runJioTV(env),
        runFancode(env),
      ]);

      return new Response(
        "Both playlists updated successfully"
      );
    } catch (e) {
      return new Response(
        "Error: " + e.toString(),
        {
          status: 500,
        }
      );
    }
  },
};
