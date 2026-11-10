import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const w = window as any;
    w.spoken = [];
    w.SpeechRecognition = class {
      onresult: any;
      onerror: any;
      onend: any;
      constructor() {
        w.recognition = this;
      }
      start() {}
      stop() {
        this.onend?.();
      }
      abort() {}
    };
    w.SpeechSynthesisUtterance = class {
      constructor(public text: string) {}
    };
    Object.defineProperty(window, "speechSynthesis", {
      value: {
        cancel() {},
        getVoices() {
          return [];
        },
        speak(value: any) {
          w.spoken.push(value.text);
          w.lastSpeech = value;
        },
      },
    });
    sessionStorage.setItem(
      "rtc-stand",
      JSON.stringify({
        id: "vja",
        name: "Vijayawada",
        code: "VJA",
        timezone: "Asia/Kolkata",
      }),
    );
  });
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const telugu =
      route.request().method() === "POST" &&
      route.request().postDataJSON()?.language === "te";
    const answer = telugu
      ? "గుంటూరుకు బస్సు బయలుదేరే సమయం 10:20. టికెట్ ధర 55 రూపాయలు."
      : "Next bus to Guntur departs at 10:20 AM, platform 4. Fare ₹55.";
    const json = path.endsWith("/app/bootstrap")
      ? { data: { sources: [], operators: [], categories: [], counts: {} } }
      : path.endsWith("/conversation/message")
        ? {
            session_id: "voice-test",
            message_id: crypto.randomUUID(),
            answer,
            response_text: answer,
            state: "ANSWERING",
            context: { state_version: 1 },
            results: [],
            warnings: [],
            intents: [],
            requires_clarification: false,
            debug: {},
            entities: {},
            context_changes: [],
            duration_ms: 1,
          }
        : { data: { candidates: [] } };
    await route.fulfill({ json });
  });
  await page.goto("/");
  await page.getByLabel("Enquiry language", { exact: true }).selectOption("en");
});

test("voice transcript submits once, reads backend reply, and supports stop and replay", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Start voice enquiry" }).click();
  await expect(
    page.getByRole("button", { name: "Stop listening" }),
  ).toBeVisible();
  await page.evaluate(() => {
    const r = (window as any).recognition;
    const callback = r.onresult;
    callback({
      resultIndex: 0,
      results: [{ isFinal: false, 0: { transcript: "Next bus" } }],
    });
  });
  await expect(page.locator(".voice-panel p")).toHaveText("Next bus");
  const request = page.waitForRequest("**/conversation/message");
  await page.evaluate(() => {
    const callback = (window as any).recognition.onresult;
    const result = {
      resultIndex: 0,
      results: [{ isFinal: true, 0: { transcript: "Next bus to Guntur" } }],
    };
    callback(result);
    callback(result);
  });
  expect((await request).postDataJSON().text).toBe("Next bus to Guntur");
  await expect(page.locator(".message.user")).toHaveCount(1);
  await expect(
    page.getByRole("button", { name: "Stop speaking" }),
  ).toBeVisible();
  expect(await page.evaluate(() => (window as any).spoken)).toEqual([
    "Next bus to Guntur departs at 10:20 AM, platform 4. Fare  rupees 55.",
  ]);
  await page.getByRole("button", { name: "Stop speaking" }).click();
  await page.getByRole("button", { name: "Read reply", exact: true }).click();
  expect(await page.evaluate(() => (window as any).spoken.length)).toBe(2);
});

test("permission errors recover and audio can be disabled", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Start voice enquiry" }).click();
  await page.evaluate(() => {
    const r = (window as any).recognition;
    r.onerror({ error: "not-allowed" });
    r.onend();
  });
  await expect(page.getByRole("alert")).toContainText(
    "Microphone access was denied",
  );
  await page.getByRole("checkbox", { name: "Read replies aloud" }).uncheck();
  await page
    .getByRole("textbox", { name: "Your enquiry" })
    .fill("Next bus to Guntur");
  await page.getByRole("button", { name: "Send enquiry" }).click();
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  expect(await page.evaluate(() => (window as any).spoken.length)).toBe(0);
});

test("unsupported recognition keeps text enquiries available on mobile", async ({
  page,
}) => {
  await page.addInitScript(() => {
    (window as any).SpeechRecognition = undefined;
    (window as any).webkitSpeechRecognition = undefined;
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Start voice enquiry" }),
  ).toBeDisabled();
  await expect(page.locator(".voice-panel")).toContainText(
    "Voice input unavailable",
  );
  await expect(
    page.getByRole("textbox", { name: "Your enquiry" }),
  ).toBeEnabled();
});

test("Telugu recognition submits native text and Ninada produces playable audio", async ({
  page,
}) => {
  test.setTimeout(180000);
  await page.getByLabel("Enquiry language", { exact: true }).selectOption("te");
  await page.getByRole("button", { name: "Start voice enquiry" }).click();
  expect(await page.evaluate(() => (window as any).recognition.lang)).toBe(
    "te-IN",
  );
  const request = page.waitForRequest("**/conversation/message");
  await page.evaluate(() =>
    (window as any).recognition.onresult({
      resultIndex: 0,
      results: [
        { isFinal: true, 0: { transcript: "గుంటూరుకు బస్సు ఎప్పుడు" } },
      ],
    }),
  );
  const body = (await request).postDataJSON();
  expect(body.language).toBe("te");
  expect(body.text).toBe("గుంటూరుకు బస్సు ఎప్పుడు");
  await expect
    .poll(
      async () => {
        const failure = await page
          .locator(".voice-controls [role=alert]")
          .allTextContents();
        if (failure.length) throw new Error(failure.join(" "));
        return page.locator(".voice-panel [role=status]").textContent();
      },
      { timeout: 120000 },
    )
    .toBe("Speaking...");
  await page.getByRole("button", { name: "Stop speaking" }).click();
  await expect(page.locator(".voice-panel [role=status]")).not.toHaveText(
    "Speaking...",
  );
});
