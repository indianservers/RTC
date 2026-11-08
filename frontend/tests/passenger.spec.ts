import { writeFileSync } from "node:fs";
import { test, expect, type Page } from "@playwright/test";

async function send(page: Page, text: string) {
  const pending = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/conversation/message") &&
      r.request().method() === "POST",
  );
  await page.getByRole("textbox", { name: "Your enquiry" }).fill(text);
  await page.getByRole("textbox", { name: "Your enquiry" }).press("Enter");
  const response = await pending;
  expect(response.ok()).toBeTruthy();
  expect(response.headers()["x-request-id"]).toMatch(/^[a-f0-9]{32}$/);
  const data = await response.json();
  await expect(page.locator(".message.assistant").last()).toContainText(
    data.answer,
  );
  return data;
}
test.beforeEach(async ({ page, context }) => {
  await context.route("**/*", (route) => {
    expect(["127.0.0.1", "localhost"]).toContain(
      new URL(route.request().url()).hostname,
    );
    return route.continue();
  });
  await page.goto("/");
  await expect(page.getByLabel("Your current bus stand")).toHaveValue(
    "Vijayawada",
  );
});

// A date-by-enquiry matrix exercises distinct server contexts, not mocked UI answers.
const followups = [
  ["next departure", "Next bus"],
  ["first departure", "First bus"],
  ["last departure", "Last bus"],
  ["known cheapest", "Cheapest bus"],
  ["fastest", "Fastest bus"],
  ["fare", "What is the fare?"],
  ["AC filter", "Only AC"],
  ["non-AC filter", "Only non AC"],
  ["sleeper filter", "Only sleeper"],
  ["seater filter", "Only seater"],
  ["fare comparison", "Fare comparison"],
  ["connections", "Connecting buses"],
  ["stops", "Route stops"],
  ["platform", "Which platform?"],
  ["duration", "Journey duration"],
  ["arrival", "Arrival time"],
  ["seat information", "Seat availability"],
  ["categories", "Available bus types"],
  ["budget filter", "Under 100 rupees"],
  ["clear category", "Any bus type"],
];
for (const days of [0, 1, 3, 7]) {
  for (const [name, utterance] of followups) {
    test(`passenger ${name}, departure date +${days}`, async ({
      page,
      request,
    }) => {
      const date = new Date();
      date.setDate(date.getDate() + days);
      const day = new Intl.DateTimeFormat("en-CA", {
        timeZone: "Asia/Kolkata",
      }).format(date);
      const first = await send(page, `Next bus to Nellore on ${day}?`);
      expect(first.requires_clarification).toBeFalsy();
      expect(first.context.origin).toBeTruthy();
      expect(first.context.travel_date).toBe(day);
      const next = await send(page, utterance);
      expect(next.session_id).toBe(first.session_id);
      expect(next.context.destination).toBe(first.context.destination);
      expect(next.context.origin).toBe(first.context.origin);
      expect(next.context.travel_date).toBe(day);
      expect(next.answer).not.toBe("");
      if (utterance === "Only AC") expect(next.context.filters.ac).toBe(true);
      if (utterance === "Only sleeper")
        expect(next.context.filters.sleeper).toBe(true);
      if (utterance === "Any bus type")
        expect(next.context.filters.ac).toBeUndefined();
      for (const result of next.results) {
        if (!result.query?.intent || result.executor) continue;
        const direct = await request.post("/api/v1/enquiry", {
          data: result.query,
        });
        expect(direct.ok()).toBeTruthy();
        const actual = await direct.json();
        expect(result.status).toBe(actual.status);
        expect(result.results).toHaveLength(actual.results.length);
        expect(result.results).toMatchObject(actual.results);
      }
      // Numeric references can only identify the current backend candidate list.
      if ((next.context.candidates?.length || 0) >= 2) {
        const current = next.context.candidates[1];
        const selected = await send(page, "Second one.");
        if (current.journey_id)
          expect(selected.context.selected_itinerary.journey_id).toBe(
            current.journey_id,
          );
        else expect(selected.context.service_id).toBe(current.service_id);
      }
      if (next.state === "NO_RESULTS")
        await expect(page.getByLabel("Suggested next questions")).toBeVisible();
    });
  }
}

for (const [name, width, height] of [
  ["desktop", 1440, 1000],
  ["tablet", 820, 1180],
  ["mobile", 390, 844],
  ["kiosk", 1920, 1080],
] as const) {
  test(`${name} enquiry and reset preserve readable local results`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height });
    await send(page, "Next bus to Nellore?");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await expect(page.locator(".bus-card").first()).toBeVisible();
    if (name === "mobile") {
      await page.getByRole("button", { name: "Kiosk touch mode" }).click();
      const region = await page.getByRole("region", {name:"Conversation"}).boundingBox();
      expect(region!.height).toBeGreaterThanOrEqual(200);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    }
    await page.getByRole("button", { name: "New conversation" }).click();
    await expect(page.locator(".message")).toHaveCount(0);
    await expect(page.getByRole("button", {name:"Jump to latest reply"})).toHaveCount(0);
    await expect(page.getByLabel("Your enquiry")).toHaveValue("");
  });
}

test("configured two-minute idle timeout expires actual passenger context", async ({
  page,
}) => {
  await page.clock.install();
  await page.getByLabel("Kiosk idle timeout").selectOption("2");
  await send(page, "Next bus to Nellore?");
  await page.clock.fastForward("02:01");
  await expect(page.locator(".message")).toHaveCount(0);
  expect(
    await page.evaluate(() => sessionStorage.getItem("rtc-session")),
  ).toBeNull();
});

test("unsent draft survives navigation but reset removes it", async ({
  page,
}) => {
  await page
    .getByLabel("Your enquiry")
    .fill("Need to reach Nellore before 8 AM");
  await page.reload();
  await expect(page.getByLabel("Your enquiry")).toHaveValue(
    "Need to reach Nellore before 8 AM",
  );
  await page.getByRole("button", { name: "New conversation" }).click();
  await expect(page.getByLabel("Your enquiry")).toHaveValue("");
});

test("category recovery asks backend and explicitly removes category restriction", async ({
  page,
}) => {
  await send(page, "Next bus to Nellore?");
  await send(page, "Only sleeper");
  const pending = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page
    .getByRole("button", { name: "Clear bus category filters", exact: true })
    .click();
  const result = await (await pending).json();
  expect(result.context.filters.ac).toBeUndefined();
  expect(result.context.candidates.length).toBeGreaterThan(0);
});

test("ambiguous destination buttons continue the original next-bus enquiry", async ({
  page,
}) => {
  const ambiguous = await send(page, "Next bus to Central?");
  expect(ambiguous.state).toBe("AWAITING_STATION_CLARIFICATION");
  expect(ambiguous.context.station_clarification.choices.length).toBe(2);
  const pending = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page
    .getByRole("button", { name: "Central (UI-CENTRAL-A)", exact: true })
    .click();
  const continued = await (await pending).json();
  expect(continued.context.destination).toBe("ui-central-a");
  expect(continued.intents).toEqual(["NEXT_BUS"]);
  expect(continued.state).toBe("NO_RESULTS");
});

test("admin unsaved form cancel warns and retains edits", async ({ page }) => {
  await page.goto("/admin/stations");
  await page
    .getByLabel("Administrator token")
    .fill("ui-test-only-token-never-for-deployment");
  await page.getByRole("button", { name: "Unlock administration" }).click();
  await page.getByRole("button", { name: "Add record" }).click();
  await page
    .getByRole("dialog")
    .getByLabel("name", { exact: true })
    .fill("Unsaved passenger station");
  await page.getByRole("button", { name: "Close form" }).click();
  const confirm = page.getByRole("dialog", {
    name: "Discard unsaved changes?",
  });
  await expect(confirm).toBeVisible();
  await confirm.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(
    page.getByRole("dialog").getByLabel("name", { exact: true }),
  ).toHaveValue("Unsaved passenger station");
  await page.getByRole("button", { name: "Close form" }).click();
  await page
    .getByRole("dialog", { name: "Discard unsaved changes?" })
    .getByRole("button", { name: /Confirm/ })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("planner reset removes restrictions without silently searching", async ({
  page,
}) => {
  await page.goto("/journeys");
  await page
    .getByText("Preferences & arrival deadline", { exact: true })
    .click();
  await page.getByLabel("Fare ceiling").fill("50");
  await page.getByRole("button", { name: "Reset search", exact: true }).click();
  await page
    .getByText("Preferences & arrival deadline", { exact: true })
    .click();
  await expect(page.getByLabel("Fare ceiling")).toHaveValue("");
  await expect(
    page.getByRole("combobox", { name: "To", exact: true }),
  ).toHaveValue("");
  await expect(page.locator(".journey-option")).toHaveCount(0);
});

test("final ten-step acceptance validates database results and context", async ({
  page,
  request,
}) => {
  const steps: unknown[] = [];
  let result = await send(page, "Next bus to Nellore?");
  const original = result.context.destination;
  steps.push({ step: 1, context: result.context, results: result.results });
  result = await send(page, "Any AC?");
  expect(result.context.filters.ac).toBe(true);
  expect(result.context.candidates.length).toBeGreaterThan(0);
  steps.push({ step: 2, context: result.context, results: result.results });
  result = await send(page, "Cheapest?");
  expect(result.context.candidates.every((r: any) => r.fare != null)).toBe(
    true,
  );
  steps.push({ step: 3, context: result.context, results: result.results });
  result = await send(page, "Tomorrow?");
  expect(result.context.destination).toBe(original);
  steps.push({ step: 4, context: result.context, results: result.results });
  const candidate = result.context.candidates[0];
  expect(candidate).toBeTruthy();
  result = await send(page, "First one.");
  expect(result.context.service_id).toBe(candidate.service_id);
  steps.push({ step: 5, context: result.context, results: result.results });
  result = await send(page, "Route stops");
  const stopResult = result.results.find(
    (r: any) => r.query?.intent === "ROUTE_STOPS",
  );
  expect(stopResult).toBeTruthy();
  const databaseStops = await request.post("/api/v1/enquiry", {
    data: stopResult.query,
  });
  expect(stopResult.results).toMatchObject(
    (await databaseStops.json()).results,
  );
  steps.push({ step: 6, context: result.context, results: result.results });
  result = await send(page, "Does it stop at Ongole?");
  expect(result.context.service_id).toBe(candidate.service_id);
  expect(result.answer).toBeTruthy();
  steps.push({ step: 7, context: result.context, results: result.results });
  result = await send(page, "Actually, Tirupati");
  expect(result.context.destination).not.toBe(original);
  expect(result.context.service_id).not.toBe(candidate.service_id);
  steps.push({ step: 8, context: result.context, results: result.results });
  result = await send(page, "Connecting buses");
  expect(result.context.destination).not.toBe(original);
  expect(result.context.filters.ac).toBe(true);
  steps.push({ step: 9, context: result.context, results: result.results });
  await page.getByRole("button", { name: "New conversation" }).click();
  await expect(page.locator(".message")).toHaveCount(0);
  expect(
    await page.evaluate(() => sessionStorage.getItem("rtc-session")),
  ).toBeNull();
  steps.push({ step: 10, display_cleared: true });
  writeFileSync(
    "../docs/phase5a-passenger-acceptance.json",
    JSON.stringify({ dataset: "ISOLATED DEMO", steps }, null, 2),
  );
});

test("local runtime performance benchmark records measured timings", async ({
  page,
  request,
  context,
}) => {
  const samples: Record<string, unknown>[] = [];
  const cdp = await context.newCDPSession(page);
  await cdp.send("Performance.enable");
  const bootstrap = await (await request.get("/api/v1/app/bootstrap")).json();
  const origin = bootstrap.data.default_station.id;
  const resolved = await (
    await request.get("/api/v1/stations/resolve?value=Nellore")
  ).json();
  const destination = resolved.data.candidates[0].id;
  for (let i = 0; i < 5; i++) {
    const nav = performance.now();
    await page.goto("/");
    await expect(page.getByLabel("Your current bus stand")).toHaveValue(
      "Vijayawada",
    );
    const pageReady = performance.now() - nav;
    const started = performance.now();
    await send(page, "Next bus to Nellore?");
    const rendered = performance.now() - started;
    const auto = performance.now();
    await page.getByLabel("Your current bus stand").fill("Tirum");
    await expect(page.getByRole("option", { name: /Tirumala/ })).toBeVisible();
    const autocomplete = performance.now() - auto;
    const diagnostic = await request.post("/api/v1/admin/ui/diagnostics", {
      headers: {
        Authorization: "Bearer ui-test-only-token-never-for-deployment",
      },
      data: {
        text: "Next bus to Nellore?",
        language: "en",
        station_context: origin,
      },
    });
    expect(diagnostic.ok()).toBeTruthy();
    const detail = await diagnostic.json();
    const planStart = performance.now();
    const planned = await request.post("/api/v1/journeys/search", {
      data: {
        origin,
        destination,
        earliest_departure: new Date().toISOString(),
        max_transfers: 2,
      },
    });
    expect(planned.ok()).toBeTruthy();
    const planner = performance.now() - planStart;
    const metrics = await cdp.send("Performance.getMetrics");
    samples.push({
      page_ready_ms: pageReady,
      chat_send_to_answer_visible_ms: rendered,
      autocomplete_including_debounce_ms: autocomplete,
      nlp_total_ms: detail.duration_ms,
      phase_timings_ms: detail.debug.timings_ms,
      planner_http_ms: planner,
      js_heap_used_bytes: metrics.metrics.find(
        (m: any) => m.name === "JSHeapUsedSize",
      )?.value,
      server_timing: diagnostic.headers()["server-timing"],
    });
  }
  writeFileSync(
    "../docs/phase5a-performance.json",
    JSON.stringify(
      {
        recorded_at: new Date().toISOString(),
        dataset: "isolated seeded DEMO SQLite",
        runs: 5,
        network: "loopback only; external browser and backend sockets blocked",
        model: "actual local configured fallback; no approved model asserted",
        samples,
      },
      null,
      2,
    ),
  );
});

test("conversation A keeps date and refuses stale second-option references", async ({
  page,
}) => {
  const initial = await send(page, "Next bus to Nellore?");
  const ac = await send(page, "Any AC?");
  expect(ac.context.filters.ac).toBe(true);
  await send(page, "Cheapest?");
  const tomorrow = await send(page, "Tomorrow?");
  const second = await send(page, "Second one.");
  expect(second.context.destination).toBe(initial.context.destination);
  expect(second.context.travel_date).toBe(tomorrow.context.travel_date);
  if (tomorrow.context.candidates.length < 2)
    expect(second.requires_clarification).toBe(true);
  else
    expect(second.context.service_id).toBe(
      tomorrow.context.candidates[1].service_id,
    );
  const stop = await send(page, "Does it stop at Ongole?");
  expect(stop.context.destination).toBe(initial.context.destination);
});

test("conversation B preserves destination and explicit transfer requirement", async ({
  page,
}) => {
  const initial = await send(page, "I need to reach Tirupati before 8 AM.");
  expect(initial.context.destination).toBeTruthy();
  const direct = await send(page, "Show direct buses.");
  expect(direct.context.destination).toBe(initial.context.destination);
  expect(direct.context.journey_max_transfers).toBe(0);
  const change = await send(page, "What if I change at Kadapa?");
  expect(change.context.destination).toBe(initial.context.destination);
  expect(change.context.transfer_station).toBeTruthy();
  expect(change.context.journey_max_transfers).toBeGreaterThan(0);
  for (const row of change.results.flatMap((r: any) => r.results))
    expect(
      row.transfers.some(
        (t: any) => t.station_id === change.context.transfer_station,
      ),
    ).toBe(true);
  const tomorrow = await send(page, "No, I meant tomorrow.");
  expect(tomorrow.context.destination).toBe(initial.context.destination);
  expect(tomorrow.context.travel_date).not.toBe(initial.context.travel_date);
});

test("conversation C category comparison keeps destination and current option numbering", async ({
  page,
}) => {
  const initial = await send(page, "How much is Super Luxury to Vizag?");
  expect(initial.context.destination).toBeTruthy();
  const cheaper = await send(page, "Any cheaper category?");
  expect(cheaper.context.destination).toBe(initial.context.destination);
  expect(cheaper.context.filters.category).toBeUndefined();
  const earliest = await send(page, "Which one leaves earliest?");
  expect(earliest.context.destination).toBe(initial.context.destination);
  const selected = await send(page, "Select the second option.");
  if ((earliest.context.candidates?.length || 0) < 2)
    expect(selected.requires_clarification).toBe(true);
  else
    expect(selected.context.service_id).toBe(
      earliest.context.candidates[1].service_id,
    );
});

test("interrupted in-flight enquiry survives reload with explicit retry", async ({
  page,
}) => {
  let release!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/conversation/message", async (route) => {
    const actual = await route.fetch();
    await held;
    try {
      await route.fulfill({ response: actual });
    } catch {
      /* old document has left */
    }
  });
  await page.getByLabel("Your enquiry").fill("Next bus to Nellore?");
  await page.getByLabel("Your enquiry").press("Enter");
  await expect(page.getByText("Checking local records…")).toBeVisible();
  await page.reload();
  release();
  await page.unroute("**/api/v1/conversation/message");
  await expect(
    page.getByText(/previous enquiry was interrupted/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Retry enquiry" }).click();
  await expect(page.locator(".bus-card").first()).toBeVisible();
  expect(
    await page.evaluate(() => sessionStorage.getItem("rtc-pending")),
  ).toBeNull();
});

test("typing renews kiosk idle deadline without retaining text after expiry", async ({
  page,
}) => {
  await page.clock.install();
  await page.getByLabel("Kiosk idle timeout").selectOption("2");
  await send(page, "Next bus to Nellore?");
  await page.clock.fastForward("01:30");
  await page.getByLabel("Your enquiry").fill("What is the fare?");
  await page.clock.fastForward("00:40");
  await expect(page.locator(".message")).not.toHaveCount(0);
  await page.clock.fastForward("01:30");
  await expect(page.locator(".message")).toHaveCount(0);
  await expect(page.getByLabel("Your enquiry")).toHaveValue("");
});
