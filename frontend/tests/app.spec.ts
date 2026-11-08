import { test, expect, type Page } from "@playwright/test";
const adminToken = "ui-test-only-token-never-for-deployment";
test.beforeEach(async ({ context, page }) => {
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (!["127.0.0.1", "localhost"].includes(url.hostname))
      throw new Error("Unexpected external request " + url.origin);
    return route.continue();
  });
  await page.goto("/");
  await expect(
    page.getByRole("combobox", { name: "Your current bus stand" }),
  ).toHaveValue("Vijayawada");
});
async function send(page: Page, text: string) {
  const pending = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/conversation/message") &&
      r.request().method() === "POST",
  );
  await page.getByRole("textbox", { name: "Your enquiry" }).fill(text);
  await page.getByRole("textbox", { name: "Your enquiry" }).press("Enter");
  const r = await pending;
  expect(r.ok()).toBeTruthy();
  const data = await r.json();
  await expect(
    page
      .getByRole("region", { name: "Conversation" })
      .getByText(data.answer, { exact: true }),
  ).toBeVisible();
  return data;
}
async function login(page: Page) {
  await page.goto("/admin");
  await page.getByLabel("Administrator token").fill(adminToken);
  await page.getByRole("button", { name: "Unlock administration" }).click();
  await expect(
    page.getByRole("heading", { name: "Administration", exact: true }),
  ).toBeVisible();
}

test("production app loads with external networking blocked", async ({
  page,
}) => {
  await expect(
    page.getByRole("heading", { name: "Where would you like to go?" }),
  ).toBeVisible();
  await expect(page.getByText("Local backend connected")).toBeVisible();
  await expect(page.locator("script[src]")).not.toHaveCount(0);
  expect(
    await page
      .locator("script[src]")
      .evaluateAll((nodes) =>
        nodes.every(
          (n) => new URL((n as HTMLScriptElement).src).hostname === "127.0.0.1",
        ),
      ),
  ).toBeTruthy();
});
test("chat sends and displays actual database service response", async ({
  page,
  request,
}) => {
  const data = await send(page, "Next bus to Nellore?");
  const rows = data.results.flatMap((r: any) => r.results || []);
  expect(
    rows.some((r: any) => r.service_id === "UI-DEMO-NELLORE"),
  ).toBeTruthy();
  await expect(
    page.locator(".bus-card").getByText("UI-DEMO-NELLORE", { exact: true }),
  ).toBeVisible();
  const detail = await request.get(
    `/api/v1/app/services/UI-DEMO-NELLORE?travel_date=${rows[0].service_date}`,
  );
  expect(detail.ok()).toBeTruthy();
});
test("follow-up retains backend destination and fare", async ({ page }) => {
  const first = await send(page, "Next bus to Nellore?");
  const next = await send(page, "What is the fare?");
  expect(next.session_id).toBe(first.session_id);
  expect(next.context.destination).toBe(first.context.destination);
  expect(
    next.results
      .flatMap((r: any) => r.results || [])
      .some((r: any) => Number(r.fare) === 125),
  ).toBeTruthy();
});
test("destination correction replaces backend destination", async ({
  page,
}) => {
  const first = await send(page, "Next bus to Nellore?");
  const next = await send(page, "Actually, Tirupati");
  expect(next.context.destination).not.toBe(first.context.destination);
  expect(
    next.context.candidates.some(
      (r: any) => r.service_id === "UI-DEMO-UNKNOWN",
    ),
  ).toBeTruthy();
});
test("new conversation resets server context", async ({ page, request }) => {
  const first = await send(page, "Next bus to Nellore?");
  const token = await page.evaluate(() => sessionStorage.getItem("rtc-owner"));
  const resetDone = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/reset"),
  );
  await page.getByRole("button", { name: "New conversation" }).click();
  await resetDone;
  await expect(
    page.getByRole("heading", { name: "Where would you like to go?" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => sessionStorage.getItem("rtc-session")),
  ).toBeNull();
  const context = await request.get(
    `/api/v1/conversation/${first.session_id}/context`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  const body = await context.json();
  expect(body.data.destination).toBeUndefined();
});
test("select bus updates authenticated backend context", async ({
  page,
  request,
}) => {
  const first = await send(page, "Next bus to Nellore?");
  const selected = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page.getByRole("button", { name: "Select this bus" }).first().click();
  const data = await (await selected).json();
  expect(data.context.selection_status).toBe("USER_CONFIRMED");
  const token = await page.evaluate(() => sessionStorage.getItem("rtc-owner"));
  const context = await request.get(
    `/api/v1/conversation/${first.session_id}/context`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  expect((await context.json()).data.service_id).toBe("UI-DEMO-NELLORE");
});
test("unknown fare remains unavailable rather than zero", async ({ page }) => {
  const data = await send(page, "Next bus to Tirupati?");
  expect(
    data.results
      .flatMap((r: any) => r.results || [])
      .find((r: any) => r.service_id === "UI-DEMO-UNKNOWN").fare,
  ).toBeNull();
  const card = page.locator(".bus-card").filter({ hasText: "UI-DEMO-UNKNOWN" });
  await expect(card.getByText("Not available", { exact: true })).toBeVisible();
  await expect(card.getByText("Fare not confirmed")).toBeVisible();
  expect(await card.textContent()).not.toContain("₹0");
});
test("fictional services carry DEMO labels", async ({ page }) => {
  await send(page, "Next bus to Nellore?");
  await expect(page.getByText("DEMO DATA", { exact: true })).toBeVisible();
  await expect(page.locator(".bus-card .badge").first()).toHaveText("DEMO");
});
test("journey details show ordered local stops", async ({ page }) => {
  await send(page, "Next bus to Nellore?");
  await page.getByRole("link", { name: "View stops" }).first().click();
  await expect(
    page.getByRole("heading", { name: "Service UI-DEMO-NELLORE" }),
  ).toBeVisible();
  await expect(page.locator(".timeline li")).toHaveCount(2);
  await expect(page.locator(".timeline li").first()).toContainText(
    "Vijayawada",
  );
  await expect(page.locator(".timeline li").last()).toContainText("Nellore");
});
test("planner shows truthful no-results for strict budget", async ({
  page,
}) => {
  await page.goto("/journeys");
  await page.getByRole("combobox", { name: "To", exact: true }).fill("Nellore");
  await page.getByRole("option").filter({ hasText: "Nellore" }).click();
  await page
    .getByText("Preferences & arrival deadline", { exact: true })
    .click();
  await page.getByLabel("Fare ceiling (INR)").fill("0");
  await page.getByRole("button", { name: "Search journeys" }).click();
  await expect(
    page.getByRole("heading", { name: "No matching journeys" }),
  ).toBeVisible();
});
test("station autocomplete queries database aliases", async ({ page }) => {
  const q = page.waitForResponse((r) =>
    r.url().includes("/stations/search?q="),
  );
  await page
    .getByRole("combobox", { name: "Your current bus stand" })
    .fill("Nellore");
  expect((await q).ok()).toBeTruthy();
  await page.getByRole("option").filter({ hasText: "Nellore" }).click();
  await expect(
    page.getByRole("combobox", { name: "Your current bus stand" }),
  ).toHaveValue("Nellore");
});
test("admin routes and mutations require backend authentication", async ({
  page,
  request,
}) => {
  await page.goto("/admin/stations");
  await expect(
    page.getByRole("heading", { name: "Administrator access" }),
  ).toBeVisible();
  expect((await request.get("/api/v1/admin/stations")).status()).toBe(401);
  expect(
    (
      await request.post("/api/v1/admin/stations", {
        data: { name: "Unauthorized" },
      })
    ).status(),
  ).toBe(401);
  await login(page);
  await page.getByRole("link", { name: "Stations", exact: true }).click();
  await expect(page.getByRole("button", { name: "Add record" })).toBeVisible();
});
test("mobile layout has no horizontal overflow and navigation works", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page
    .getByRole("link", { name: "Journey planner", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Every leg, one clear journey" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});
test("keyboard composer sends on Enter and supports multiline", async ({
  page,
}) => {
  const input = page.getByRole("textbox", { name: "Your enquiry" });
  await input.focus();
  await page.keyboard.type("Next bus to Nellore?");
  await page.keyboard.press("Shift+Enter");
  await expect(input).toHaveValue("Next bus to Nellore?\n");
  await page.keyboard.press("Enter");
  await expect(page.locator(".bus-card").first()).toBeVisible();
});
test("authenticated CSV dry run reports validation without inserts", async ({
  page,
  request,
}) => {
  await login(page);
  await page.getByRole("link", { name: "Data Imports", exact: true }).click();
  await page
    .getByLabel("CSV content")
    .fill(
      "code,name,timezone,dataset_source\nUI-DRY,UI dry-run station,Asia/Kolkata,DEMO",
    );
  await page.getByRole("button", { name: "Validate CSV" }).click();
  await expect(page.getByLabel("Import result")).toContainText("dry_run");
  const stations = await request.get("/api/v1/stations/search?q=UI%20dry-run");
  expect((await stations.json()).data).toHaveLength(0);
});

test("authorized admin creates edits and deactivates actual records", async ({
  page,
  request,
}) => {
  await login(page);
  await page.getByRole("link", { name: "RTC Operators", exact: true }).click();
  await page.getByRole("button", { name: "Add record" }).click();
  await page
    .getByRole("dialog")
    .getByLabel("dataset source", { exact: true })
    .fill("DEMO");
  await page
    .getByRole("dialog")
    .getByLabel("code", { exact: true })
    .fill("UI-OP");
  await page
    .getByRole("dialog")
    .getByLabel("name", { exact: true })
    .fill("UI Browser operator");
  await page.getByRole("button", { name: "Save record" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByLabel("Search records").fill("UI Browser operator");
  await page.getByRole("button", { name: "Edit UI Browser operator" }).click();
  await page
    .getByRole("dialog")
    .getByLabel("name", { exact: true })
    .fill("UI Browser updated");
  await page.getByRole("button", { name: "Save record" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByLabel("Search records").fill("UI Browser updated");

  await page
    .getByRole("button", { name: "Deactivate UI Browser updated", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm", exact: true }).click();
  await expect(
    page.getByRole("table").getByText("Inactive", { exact: true }),
  ).toBeVisible();
  const response = await request.get("/api/v1/admin/operators", {
    headers: { Authorization: `Bearer ${adminToken}` },
  });
  expect(
    (await response.json()).data.find((r: any) => r.code === "UI-OP").active,
  ).toBe(false);
});
test("admin diagnostics invokes the actual guarded NLP adapter", async ({
  page,
}) => {
  await login(page);
  await page
    .getByRole("link", { name: "NLP Diagnostics", exact: true })
    .click();
  await page.getByLabel("Passenger message").fill("Next bus to Nellore?");
  const done = page.waitForResponse((r) =>
    r.url().endsWith("/admin/ui/diagnostics"),
  );
  await page.getByRole("button", { name: "Run local diagnostics" }).click();
  const response = await done;
  expect(response.status()).toBe(200);
  expect((await response.json()).debug).toBeTruthy();
  await expect(
    page.getByText("Not calibrated / not available", { exact: true }),
  ).toBeVisible();
});
test("failed enquiry offers retry and then uses the real API", async ({
  page,
}) => {
  let failed = false;
  await page.route("**/api/v1/conversation/message", (route) => {
    if (!failed) {
      failed = true;
      return route.abort("failed");
    }
    return route.continue();
  });
  await page
    .getByRole("textbox", { name: "Your enquiry" })
    .fill("Next bus to Nellore?");
  await page.getByRole("button", { name: "Send enquiry" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Cannot reach the local RTC backend",
  );
  await page.getByRole("button", { name: "Retry enquiry" }).click();
  await expect(
    page.locator(".bus-card").getByText("UI-DEMO-NELLORE", { exact: true }),
  ).toBeVisible();
});

test("selected stand and owned session stay aligned after reload", async ({
  page,
}) => {
  await send(page, "Next bus to Nellore?");
  const picker = page.getByRole("combobox", { name: "Your current bus stand" });
  await picker.fill("Tirumala");
  const update = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page.getByRole("option").filter({ hasText: "Tirumala" }).click();
  const before = (await (await update).json()).context.origin;
  await page.reload();
  await expect(
    page.getByRole("combobox", { name: "Your current bus stand" }),
  ).toHaveValue("Tirumala");
  const next = await send(page, "What is the fare?");
  expect(next.context.origin).toBe(before);
});

async function plannerSearch(page: Page) {
  await page.goto("/journeys");
  await page.getByRole("combobox", { name: "To", exact: true }).fill("Nellore");
  await page.getByRole("option").filter({ hasText: "Nellore" }).click();
  await page.getByRole("button", { name: "Search journeys" }).click();
  await expect(page.locator(".journey-option").first()).toBeVisible();
}
test("selected service strip persists and correction invalidates selection", async ({
  page,
}) => {
  await send(page, "Next bus to Nellore?");
  const selected = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page.getByRole("button", { name: "Select this bus" }).first().click();
  await selected;
  await expect(page.getByLabel("Active enquiry context")).toContainText(
    "Selected service",
  );
  const correction = await send(page, "Actually, Tirupati");
  expect(correction.context.service_id).not.toBe("UI-DEMO-NELLORE");
  await expect(page.getByLabel("Active enquiry context")).not.toContainText(
    "UI-DEMO-NELLORE",
  );
});
test("planner comparison validates choices and avoids missing-fare winner", async ({
  page,
}) => {
  await plannerSearch(page);
  const options = page.locator(".journey-option");
  const known = options
    .filter({ hasText: "UI-DEMO-NELLORE" })
    .filter({ hasNotText: "UI-DEMO-NELLORE-UNKNOWN" })
    .first();
  const unknown = options
    .filter({ hasText: "UI-DEMO-NELLORE-UNKNOWN" })
    .first();
  await known.locator("input[type=checkbox]").check();
  await unknown.locator("input[type=checkbox]").check();
  const validation = page.waitForResponse((r) =>
    r.url().endsWith("/journeys/compare"),
  );
  await page.getByRole("button", { name: "Compare journeys (2)" }).click();
  expect((await validation).status()).toBe(200);
  const panel = page.getByLabel("Journey comparison");
  await expect(panel).toBeVisible();
  await expect(
    panel.getByText("Not available", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    panel.getByText("Lowest known fare", { exact: true }),
  ).toHaveCount(0);
});
test("shortest-duration ranking and hard filters use actual planner API", async ({
  page,
}) => {
  await plannerSearch(page);
  const request = page.waitForRequest(
    (r) => r.url().endsWith("/journeys/search") && r.method() === "POST",
  );
  await page
    .getByRole("button", { name: "Shortest duration", exact: true })
    .click();
  expect((await request).postDataJSON().ranking).toBe("SHORTEST_DURATION");
  await page
    .getByText("Preferences & arrival deadline", { exact: true })
    .click();
  await page.getByLabel("Fare ceiling (INR)").fill("1");
  await page.getByRole("button", { name: "Search journeys" }).click();
  await expect(
    page.getByRole("heading", { name: "No matching journeys" }),
  ).toBeVisible();
  await expect(page.getByLabel("Fare ceiling (INR)")).toHaveValue("1");
});
test("service tabs support keyboard and preserve route stop ordering", async ({
  page,
}) => {
  await send(page, "Next bus to Nellore?");
  await page
    .getByRole("link", { name: "View details", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("tab", { name: "Overview", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await page.getByRole("tab", { name: "Route & Stops", exact: true }).click();
  await expect(page.locator(".timeline li")).toHaveCount(2);
  await page.getByRole("tab", { name: "Route & Stops", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(
    page.getByRole("tab", { name: "Fares", exact: true }),
  ).toBeFocused();
  await expect(page.getByRole("tabpanel")).toContainText(
    "Full listed route fare",
  );
  await page.getByRole("tab", { name: "Amenities", exact: true }).click();
  await expect(page.getByRole("tabpanel")).toContainText(
    "No verified amenity properties",
  );
  await page
    .getByRole("tab", { name: "Operational Status", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Refresh local status" }),
  ).toBeVisible();
});
test("data quality displays actual issue records and filtered checks", async ({
  page,
}) => {
  await login(page);
  await page.getByRole("link", { name: "Data Quality", exact: true }).click();
  await expect(page.locator(".quality-issue").first()).toBeVisible();
  await page.getByLabel("Issue type").selectOption("MISSING_ROUTE_STOPS");
  await expect(
    page.locator(".quality-issue").filter({ hasText: "UI-QUALITY-ROUTE" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Issue details", exact: true })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toContainText("Add at least two");
  await page.getByRole("button", { name: "Close record details" }).click();
  await page
    .getByRole("link", { name: "Open affected records", exact: true })
    .first()
    .click();
  await expect(page.locator("tbody")).toContainText("UI-QUALITY-ROUTE");
});
test("server-side admin search finds records beyond the first page", async ({
  page,
}) => {
  await login(page);
  await page.getByRole("link", { name: "Stations", exact: true }).click();
  await page.getByLabel("Search records").fill("Quality station 6");
  await expect(page.locator("tbody")).toContainText("Quality station 6");
  await page
    .getByRole("button", { name: "View record details", exact: true })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toContainText("UI-QUALITY-6");
});
test("kiosk mode and automatic expiry clear private conversation", async ({
  page,
}) => {
  await page.clock.install();
  await page.getByRole("button", { name: "Kiosk touch mode" }).click();
  await send(page, "Next bus to Nellore?");
  await expect(page.locator(".app-shell")).toHaveClass(/kiosk-mode/);
  await page.clock.fastForward("16:00");
  await expect(
    page.getByRole("heading", { name: "Where would you like to go?" }),
  ).toBeVisible();
  await expect(page.locator(".message")).toHaveCount(0);
  expect(
    await page.evaluate(() => sessionStorage.getItem("rtc-session")),
  ).toBeNull();
});
test("clear-context dialog removes passenger data and resets backend", async ({
  page,
}) => {
  const result = await send(page, "Next bus to Nellore?");
  const reset = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/reset"),
  );
  await page
    .getByRole("button", { name: "Clear context", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Confirm", exact: true }).click();
  expect((await reset).status()).toBe(200);
  await expect(
    page.getByRole("heading", { name: "Where would you like to go?" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => sessionStorage.getItem("rtc-session")),
  ).not.toBe(result.session_id);
});
test("contextual stop action invokes actual backend route enquiry", async ({
  page,
}) => {
  await send(page, "Next bus to Nellore?");
  const done = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page
    .getByRole("button", { name: "View intermediate stops", exact: true })
    .click();
  const response = await (await done).json();
  expect(response.results.some((r: any) => r.intent === "ROUTE_STOPS")).toBe(
    true,
  );
});

test("known comparable fares receive a factual winner and three-option limit", async ({
  page,
}) => {
  await plannerSearch(page);
  const options = page.locator(".journey-option");
  const base = options
    .filter({ hasText: "UI-DEMO-NELLORE" })
    .filter({ hasNotText: "UI-DEMO-NELLORE-CHEAP" })
    .filter({ hasNotText: "UI-DEMO-NELLORE-UNKNOWN" })
    .first();
  const cheap = options.filter({ hasText: "UI-DEMO-NELLORE-CHEAP" }).first();
  await base.locator("input[type=checkbox]").check();
  await cheap.locator("input[type=checkbox]").check();
  await page.getByRole("button", { name: "Compare journeys (2)" }).click();
  const comparison = page.getByLabel("Journey comparison");
  await expect(
    comparison.getByText("Lowest known fare", { exact: true }),
  ).toHaveCount(1);
  await expect(comparison.getByText("₹95.00", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Close comparison" }).click();
  await options
    .filter({ hasText: "UI-DEMO-NELLORE-UNKNOWN" })
    .first()
    .locator("input[type=checkbox]")
    .check();
  await expect(
    page.getByRole("button", { name: "Compare journeys (3)" }),
  ).toBeEnabled();
  const unchecked = page.locator(".compare-select input:not(:checked)");
  if (await unchecked.count()) await expect(unchecked.first()).toBeDisabled();
});
test("reset clears private data even when backend reset is unavailable", async ({
  page,
}) => {
  await send(page, "Next bus to Nellore?");
  const old = await page.evaluate(() => sessionStorage.getItem("rtc-owner"));
  await page.route("**/conversation/reset", (r) => r.abort("failed"));
  await page.getByRole("button", { name: "New conversation" }).click();
  await expect(page.locator(".message")).toHaveCount(0);
  await expect(page.getByRole("alert")).toContainText(
    "Conversation cleared on this device",
  );
  expect(
    await page.evaluate(() => sessionStorage.getItem("rtc-owner")),
  ).not.toBe(old);
  expect(
    await page.evaluate(() => sessionStorage.getItem("rtc-session")),
  ).toBeNull();
});
test("a late actual response cannot restore a reset conversation", async ({
  page,
}) => {
  let ready!: () => void;
  let release!: () => void;
  const captured = new Promise<void>((resolve) => (ready = resolve));
  const wait = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/conversation/message", async (route) => {
    const actual = await route.fetch();
    ready();
    await wait;
    await route.fulfill({ response: actual }).catch(() => {});
  });
  await page
    .getByRole("textbox", { name: "Your enquiry" })
    .fill("Next bus to Nellore?");
  await page.getByRole("button", { name: "Send enquiry" }).click();
  await captured;
  await page.getByRole("button", { name: "New conversation" }).click();
  release();
  await expect(
    page.getByRole("heading", { name: "Where would you like to go?" }),
  ).toBeVisible();
  await expect(page.locator(".message")).toHaveCount(0);
  expect(
    await page.evaluate(() => sessionStorage.getItem("rtc-session")),
  ).toBeNull();
});
test("invalid CSV reports actual row errors without committing", async ({
  page,
  request,
}) => {
  await login(page);
  await page.getByRole("link", { name: "Data Imports", exact: true }).click();
  await page
    .getByLabel("CSV content")
    .fill(
      "code,name,timezone,dataset_source\nBROKEN,Invalid timezone,Not/A_Zone,DEMO",
    );
  await page.getByRole("button", { name: "Validate CSV" }).click();
  await expect(page.getByRole("alert")).toContainText("No rows were committed");
  await expect(page.getByLabel("Import result")).toContainText(
    '"committed": false',
  );
  const result = await request.get(
    "/api/v1/stations/search?q=Invalid%20timezone",
  );
  expect((await result.json()).data).toHaveLength(0);
});
test("kiosk touch layout has no overflow and sufficiently large restart", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Kiosk touch mode" }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(
    (await page
      .getByRole("button", { name: "New conversation" })
      .boundingBox())!.height,
  ).toBeGreaterThanOrEqual(44);
});

test("bus-card compare uses the full route rather than selected bus only", async ({
  page,
}) => {
  await send(page, "Next bus to Nellore?");
  const done = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page
    .getByRole("button", { name: "Compare", exact: true })
    .first()
    .click();
  const data = await (await done).json();
  const rows = data.results.flatMap((r: any) => r.results || []);
  expect(rows.filter((r: any) => r.fare != null).length).toBeGreaterThanOrEqual(
    2,
  );
  expect(rows.some((r: any) => r.service_id === "UI-DEMO-NELLORE-CHEAP")).toBe(
    true,
  );
  expect(rows.some((r: any) => r.fare == null)).toBe(false);
});

test("verified operational data expires in the UI at its actual deadline", async ({
  page,
}) => {
  await page.clock.install();
  const result = await send(page, "Next bus to Nellore?");
  const row = result.results
    .flatMap((r: any) => r.results || [])
    .find((r: any) => r.service_id === "UI-DEMO-NELLORE");
  const details = page.waitForResponse((r) =>
    r.url().includes("/app/services/UI-DEMO-NELLORE?"),
  );
  await page.goto(
    `/services/UI-DEMO-NELLORE?date=${row.service_date}&tab=operations`,
  );
  const data = (await (await details).json()).data;
  expect(data.operational_expires_at).toBeTruthy();
  await expect(page.getByRole("tabpanel")).toContainText("12 minutes");
  const browserNow = await page.evaluate(() => Date.now());
  await page.clock.fastForward(
    Math.max(1, Date.parse(data.operational_expires_at) - browserNow + 1000),
  );
  await expect(page.locator(".status-indicator .badge").first()).toContainText(
    "STALE",
  );
  await expect(page.getByRole("tabpanel")).toContainText("Not confirmed");
});
