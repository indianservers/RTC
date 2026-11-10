import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  testMatch: "voice.spec.ts",
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:5183", headless: true },
  webServer: {
    command:
      process.env.RTC_VOICE_PREVIEW === "1"
        ? "npm run preview -- --port 5183"
        : "npm run dev -- --port 5183",
    url: "http://127.0.0.1:5183",
    reuseExistingServer: true,
  },
});
