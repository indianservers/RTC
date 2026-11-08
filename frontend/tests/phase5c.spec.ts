import { test, expect, type Page } from "@playwright/test";

async function send(page: Page, text: string) {
  const pending = page.waitForResponse(
    (r) =>
      r.url().endsWith("/conversation/message") &&
      r.request().method() === "POST",
  );
  await page.getByRole("textbox", { name: "Your enquiry" }).fill(text);
  await page.getByRole("textbox", { name: "Your enquiry" }).press("Enter");
  const response = await pending;
  expect(response.ok()).toBeTruthy();
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

test("Phase 5C ten-turn acceptance retains exact references and corrections", async ({
  page,
}) => {
  let response = await send(page, "Next bus to Nellore?");
  const sid = response.session_id;
  const chosen = response.result_set[1];
  response = await send(page, "Second one.");
  expect(response.selected_journey.service_id).toBe(chosen.service_id);
  response = await send(page, "How much?");
  expect(Number(response.results[0].results[0].amount)).toBe(
    Number(chosen.fare),
  );
  response = await send(page, "Does it have AC?");
  expect(response.selected_journey.service_id).toBe(chosen.service_id);
  response = await send(page, "When will it arrive?");
  expect(response.results[0].results[0].arrival).toBe(chosen.arrival);
  response = await send(page, "Compare with the first one.");
  expect(response.dialogue_act).toBe("COMPARISON");
  expect(response.results[0].results.map((r: any) => r.result_id)).toContain(
    chosen.result_id,
  );
  await page
    .locator(".conversation-details")
    .last()
    .getByText("Compare recorded journey facts")
    .click();
  await expect(page.locator(".comparison-facts")).toBeVisible();
  response = await send(page, "What about tomorrow?");
  expect(response.selected_journey).toBeNull();
  response = await send(page, "Only Super Luxury.");
  response = await send(page, "No, I meant Tirupati.");
  expect(response.context.destination_name).toBe("Tirupati");
  response = await send(page, "Summarize my journey.");
  expect(response.session_id).toBe(sid);
  expect(response.dialogue_act).toBe("SUMMARY");
  expect(response.context.destination_name).toBe("Tirupati");
  expect(response.selected_journey).toBeNull();
});

test("Compositional answer details use the same trips and preserve unknown platforms", async ({
  page,
}) => {
  const response = await send(page, "Next bus to Nellore, fare and platform?");
  expect(response.query_plan.primary_intent).toBe("NEXT_BUS");
  expect(response.answer_sections).toHaveLength(3);
  const primary = response.results.find((r: any) => r.intent === "NEXT_BUS");
  const fare = response.results.find((r: any) => r.intent === "TICKET_FARE");
  expect(fare.results.map((r: any) => r.service_id)).toEqual(
    primary.results.map((r: any) => r.service_id),
  );
  await page.getByText("Answer details · 3 topics").click();
  await expect(
    page
      .locator(".conversation-details")
      .getByRole("heading", { name: "Bus Platform" }),
  ).toBeVisible();
});

test("Unrelated questions retain selection, summary and valid fare followup", async ({
  page,
}) => {
  await send(page, "Next bus to Nellore?");
  const selected = await send(page, "2");
  const outside = await send(page, "Who is the Prime Minister?");
  expect(outside.dialogue_act).toBe("OUT_OF_SCOPE");
  expect(outside.results).toHaveLength(0);
  expect(outside.selected_journey.service_id).toBe(
    selected.selected_journey.service_id,
  );
  const summary = await send(page, "What have we selected?");
  expect(summary.dialogue_act).toBe("SUMMARY");
  expect(summary.selected_journey.service_id).toBe(
    selected.selected_journey.service_id,
  );
  const fare = await send(page, "How much?");
  expect(fare.results[0].query.service_id).toBe(
    selected.selected_journey.service_id,
  );
});

test("Unknown category offers database choices and survives a destination correction", async ({
  page,
}) => {
  await send(page, "Next bus to Nellore tomorrow?");
  await send(page, "2");
  const unknown = await send(page, "Only imaginary premium");
  expect(unknown.state).toBe("AWAITING_CATEGORY");
  expect(unknown.selected_journey).toBeNull();
  expect(unknown.clarification_choices.length).toBeGreaterThan(0);
  const corrected = await send(page, "No, I meant Tirupati");
  expect(corrected.context.unresolved_category).toBe("imaginary premium");
  expect(corrected.results).toHaveLength(0);
  const choice = corrected.clarification_choices[0];
  const pending = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page
    .locator(".message.assistant")
    .last()
    .getByRole("button", { name: choice.label, exact: true })
    .click();
  const resolved = await (await pending).json();
  expect(resolved.context.filters.category).toBe(choice.id);
  expect(resolved.context.unresolved_category).toBeUndefined();
});
