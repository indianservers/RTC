import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  expect: { timeout: 12000 },
  reporter: [
    ["list"],
    ["json", { outputFile: "../docs/phase5d-playwright.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:8020",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    ...devices["Desktop Chrome"],
  },
  webServer: [
    {
      command: "python ../scripts/serve_ui_test.py",
      url: "http://127.0.0.1:8020/api/v1/nlp/health",
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: "python ../scripts/serve_ui_test.py --port 8021 --strict",
      url: "http://127.0.0.1:8021/api/v1/nlp/health",
      reuseExistingServer: false,
      timeout: 60000,
    },
  ],
});
