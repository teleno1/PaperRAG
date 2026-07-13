import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:8765",
    channel: "chrome",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8765",
    cwd: "..",
    url: "http://127.0.0.1:8765/",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
