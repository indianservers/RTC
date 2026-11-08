import { test, expect, type Page } from "@playwright/test";

async function send(page: Page, text: string) {
  const pending = page.waitForResponse(
    (r) =>
      r.url().endsWith("/conversation/message") &&
      r.request().method() === "POST",
  );
  const composer = page.getByRole("textbox", { name: "Your enquiry" });
  await composer.fill(text);
  await composer.press("Enter");
  const response = await pending;
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  await expect(page.locator(".message.assistant").last()).toContainText(
    data.response_text,
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

test("option two keeps its exact segment through fare, facilities and corrections", async ({
  page,
}) => {
  let previous = await send(page, "Next bus to Nellore?");
  const sid = previous.session_id;
  expect(previous.result_set.length).toBeGreaterThanOrEqual(2);
  const chosen = previous.result_set[1];
  previous = await send(page, "2");
  expect(previous.selected_journey.service_id).toBe(chosen.service_id);
  for (const question of [
    "What is the fare?",
    "Is it AC?",
    "Does it stop at Ongole?",
  ]) {
    const response = await send(page, question);
    expect(response.session_id).toBe(sid);
    expect(response.context.state_version).toBe(
      previous.context.state_version + 1,
    );
    expect(response.selected_journey.service_id).toBe(chosen.service_id);
    expect(response.results[0].query.segments[0]).toMatchObject({
      service_id: chosen.service_id,
      origin: chosen.origin_id,
      destination: chosen.destination_id,
    });
    expect(response.data_source).toContain("DEMO");
    if (question.includes("fare")) {
      expect(Number(response.results[0].results[0].amount)).toBe(
        Number(chosen.fare),
      );
      expect(response.answer).toContain("selected");
    }
    previous = response;
  }
  previous = await send(page, "What about tomorrow?");
  expect(previous.selected_journey).toBeNull();
  expect(previous.context.destination).toBe(chosen.destination_id);
  previous = await send(page, "Cheapest option?");
  expect(previous.session_id).toBe(sid);
  const correction = await send(page, "No, I meant Tirupati.");
  expect(correction.context.destination).not.toBe(chosen.destination_id);
  expect(correction.selected_journey).toBeNull();
  await expect(page.locator(".selected-context")).toContainText("Tirupati");
});

test("unknown selected fare explains the missing record", async ({ page }) => {
  const first = await send(page, "Next bus to Nellore?");
  const index = first.result_set.findIndex(
    (r: any) => r.service_id === "UI-DEMO-NELLORE-UNKNOWN",
  );
  expect(index).toBeGreaterThanOrEqual(0);
  const selected = await send(page, String(index + 1));
  const fare = await send(page, "Fare?");
  expect(fare.selected_journey.service_id).toBe(
    selected.selected_journey.service_id,
  );
  expect(fare.results[0].results[0].amount).toBeNull();
  expect(fare.answer).toContain("fare for that service is not available");
  expect(fare.answer).not.toContain("No matching");
  await expect(
    page.getByRole("button", { name: "Any cheaper?", exact: true }),
  ).toBeVisible();
});

test("backend filter chips issue a typed clear action", async ({ page }) => {
  await send(page, "Next bus to Nellore?");
  await send(page, "Only AC");
  const pending = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page
    .getByRole("button", { name: "Remove ac filter", exact: true })
    .click();
  const response = await pending;
  expect(response.request().postDataJSON().context_action).toEqual({
    op: "CLEAR_SLOT",
    slot: "ac",
  });
  const data = await response.json();
  expect(data.context.filters.ac).toBeUndefined();
  await expect(
    page.getByRole("button", { name: "Remove ac filter", exact: true }),
  ).toHaveCount(0);
});

test("reload preserves backend selection and personal mode is acknowledged", async ({
  page,
}) => {
  const first = await send(page, "Next bus to Nellore?");
  const selected = await send(page, "2");
  await page.reload();
  await expect(page.getByLabel("Your current bus stand")).toHaveValue(
    "Vijayawada",
  );
  const fare = await send(page, "Fare?");
  expect(fare.session_id).toBe(first.session_id);
  expect(fare.selected_journey.service_id).toBe(
    selected.selected_journey.service_id,
  );
  const pending = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page.getByLabel("Conversation privacy mode").selectOption("personal");
  const mode = await (await pending).json();
  expect(mode.context.session_mode).toBe("personal");
  expect(mode.session_id).toBe(first.session_id);
  expect(
    Date.parse(mode.context.expires_at) -
      Date.parse(mode.context.last_activity_at),
  ).toBe(86400000);
});

test("version conflict restores real server history and exact selected journey", async ({
  page,
  request,
}) => {
  await send(page, "Next bus to Nellore?");
  const selected = await send(page, "2");
  const owner = await page.evaluate(() => sessionStorage.getItem("rtc-owner"));
  const advanced = await request.post("/api/v1/conversation/message", {
    data: {
      session_id: selected.session_id,
      text: "Fare?",
      language: "en",
      owner_token: owner,
      expected_state_version: selected.context.state_version,
      client_message_id: crypto.randomUUID(),
    },
  });
  expect(advanced.ok()).toBeTruthy();
  const actual = await advanced.json();
  const pending = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page.getByRole("textbox", { name: "Your enquiry" }).fill("Fare?");
  await page.getByRole("button", { name: "Send enquiry", exact: true }).click();
  expect((await pending).status()).toBe(409);
  const restore = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/state"),
  );
  await page
    .getByRole("button", { name: "Restore saved context", exact: true })
    .click();
  const saved = await (await restore).json();
  expect(saved.state_version).toBe(actual.context.state_version);
  expect(saved.selected_journey.service_id).toBe(
    selected.selected_journey.service_id,
  );
  await expect(
    page.getByText(
      "Saved messages and context restored. New questions will recheck current database records.",
    ),
  ).toBeVisible();
  const fresh = await send(page, "Fare?");
  expect(fresh.context.state_version).toBe(saved.state_version + 1);
  expect(fresh.selected_journey.service_id).toBe(
    selected.selected_journey.service_id,
  );
  expect(fresh.results[0].results[0].amount).toBe(
    actual.results[0].results[0].amount,
  );
});
