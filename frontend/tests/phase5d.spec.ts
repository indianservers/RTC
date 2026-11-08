import { test, expect, type Page } from "@playwright/test";
const token = "ui-test-only-token-never-for-deployment";
async function send(page: Page, text: string) {
  const pending = page.waitForResponse(
    (r) =>
      r.url().endsWith("/conversation/message") &&
      r.request().method() === "POST",
  );
  const field = page.getByRole("textbox", { name: "Your enquiry" });
  await field.fill(text);
  await field.press("Enter");
  const response = await pending;
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  await expect(page.locator(".message.assistant").last()).toContainText(
    data.answer,
  );
  return data;
}
async function admin(page: Page) {
  await page.goto("/admin/nlp-review");
  await page.getByLabel("Administrator token").fill(token);
  await page.getByRole("button", { name: "Unlock administration" }).click();
  await expect(
    page.getByRole("heading", { name: "NLP review and reliability" }),
  ).toBeVisible();
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

test("recovery, exact fare, optional feedback, local review and approved export", async ({
  page,
}) => {
  const first = await send(page, "Next bus to Nellore?");
  const last = await send(page, "No, I meant the last bus.");
  expect(last.intents).toEqual(["LAST_BUS"]);
  expect(last.context.destination).toBe(first.context.destination);
  const selected = await send(page, "1");
  const fare = await send(page, "Fare?");
  expect(fare.results[0].query.service_id).toBe(selected.context.service_id);
  const wrong = await send(page, "That's the wrong bus.");
  expect(wrong.selected_journey).toBeNull();
  expect(wrong.requires_clarification).toBeTruthy();
  await send(page, "Next bus");
  const corrected = await send(page, "2");
  const platform = await send(page, "Which platform?");
  expect(platform.results[0].query.service_id).toBe(
    corrected.context.service_id,
  );
  const message = page.locator(".message.assistant").last();
  await message.getByLabel("Include my question for review").check();
  const pending = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/feedback"),
  );
  await message.getByLabel("Report a reply issue").selectOption("WRONG_INTENT");
  const saved = await (await pending).json();
  expect(saved.saved).toBeTruthy();
  await expect(
    message.getByText("Feedback saved locally. Thank you."),
  ).toBeVisible();
  await admin(page);
  const row = page.getByRole("row").filter({ hasText: "Which platform?" });
  await row.getByRole("button", { name: "Review", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Review status", exact: true })
    .selectOption("APPROVED_FOR_TRAINING");
  await page
    .getByLabel("Corrected intent", { exact: true })
    .fill("BUS_PLATFORM");
  await page
    .getByLabel("Reviewer notes")
    .fill(
      "Synthetic DEMO browser acceptance label; eligible only for future reviewed candidate work.",
    );
  const review = page.waitForResponse((r) =>
    r.url().includes(`/reviews/${saved.id}/review`),
  );
  await page.getByRole("button", { name: "Save review", exact: true }).click();
  expect((await (await review).json()).data.training_eligible).toBeTruthy();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export approved feedback" }).click();
  expect((await download).suggestedFilename()).toBe("reviewed-feedback.jsonl");
  await expect(
    page.getByRole("heading", {
      name: "Training candidates and deployment history",
    }),
  ).toBeVisible();
});

test("no-result diagnostic preserves fare ceiling and recovery is explicit", async ({
  page,
}) => {
  await send(page, "Next bus to Nellore tomorrow?");
  const empty = await send(page, "Under 1");
  expect(empty.state).toBe("NO_RESULTS");
  expect(
    empty.reliability.diagnosis.some((d: any) => d.code === "FARE_LIMIT"),
  ).toBeTruthy();
  expect(Number(empty.context.filters.max_fare)).toBe(1);
  const pending = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page
    .getByRole("button", { name: "Remove fare limit", exact: true })
    .click();
  const recovered = await (await pending).json();
  expect(recovered.context.filters.max_fare).toBeUndefined();
  expect(recovered.result_set.length).toBeGreaterThan(0);
});

test("uncertainty gives an actionable first-versus-next clarification", async ({
  page,
}) => {
  await send(page, "Next bus to Nellore tomorrow?");
  const uncertain = await send(page, "First or next bus?");
  expect(uncertain.requires_clarification).toBeTruthy();
  const pending = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/message"),
  );
  await page
    .locator(".message.assistant")
    .last()
    .getByRole("button", { name: "First bus of the day", exact: true })
    .click();
  const first = await (await pending).json();
  expect(first.intents).toEqual(["FIRST_BUS"]);
  expect(first.reliability.probability).toBeNull();
});

test("admin deletion controls remove retained question and training eligibility", async ({
  page,
}) => {
  await send(page, "Next bus to Nellore?");
  const message = page.locator(".message.assistant").last();
  await message.getByLabel("Include my question for review").check();
  const saved = page.waitForResponse((r) =>
    r.url().endsWith("/conversation/feedback"),
  );
  await message
    .getByRole("button", { name: "Not helpful", exact: true })
    .click();
  await saved;
  await admin(page);
  await page
    .getByRole("row")
    .filter({ hasText: "Next bus to Nellore?" })
    .last()
    .getByRole("button", { name: "Review", exact: true })
    .click();
  const pending = page.waitForResponse((r) => r.url().endsWith("/anonymize"));
  await page.getByRole("button", { name: "Anonymize retained text" }).click();
  expect((await (await pending).json()).data.training_eligible).toBeFalsy();
});
