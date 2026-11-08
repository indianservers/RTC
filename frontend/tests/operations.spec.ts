import { test, expect, type Page } from "@playwright/test";
const auth = {
  Authorization: "Bearer ui-test-only-token-never-for-deployment",
};
test.use({ baseURL: "http://127.0.0.1:8021" });
async function login(page: Page) {
  await page.goto("/admin/operations");
  await page
    .getByLabel("Administrator token")
    .fill("ui-test-only-token-never-for-deployment");
  await page.getByRole("button", { name: "Unlock administration" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Operations Control Center",
      exact: true,
    }),
  ).toBeVisible();
  const op = await page
    .getByLabel("Board operator", { exact: true })
    .locator("option")
    .nth(1)
    .getAttribute("value");
  await page.getByLabel("Board operator", { exact: true }).selectOption(op!);
}
async function action(
  page: Page,
  service: string,
  kind: string,
  fields?: () => Promise<void>,
) {
  await page
    .getByRole("button", { name: `Dispatch ${service}`, exact: true })
    .click();
  const panel = page.getByRole("region", { name: "Dispatcher quick actions" });
  await panel
    .getByLabel("Operational action", { exact: true })
    .selectOption(kind);
  await panel
    .getByLabel("Operational source", { exact: true })
    .selectOption("ui-expiry-source");
  await panel
    .getByLabel("Reason", { exact: true })
    .fill("DEMO observed by local test dispatcher");
  if (fields) await fields();
  await panel
    .getByRole("button", { name: "Review operational update" })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: /Confirm/ })
    .click();
  await expect(
    page.getByText(new RegExp(`Recorded ${kind} · version`)),
  ).toBeVisible();
}
test.beforeEach(async ({ context }) => {
  await context.route("**/*", (route) => {
    expect(["127.0.0.1", "localhost"]).toContain(
      new URL(route.request().url()).hostname,
    );
    return route.continue();
  });
});

test("disruption request is published only by an independent station supervisor", async ({
  page,
  request,
}) => {
  await login(page);
  await page
    .getByLabel("Search board", { exact: true })
    .fill("UI-DEMO-NELLORE-UNKNOWN");
  await action(page, "UI-DEMO-NELLORE-UNKNOWN", "NOTICE_REQUEST", async () => {
    await page
      .getByLabel("Notice description", { exact: true })
      .fill("DEMO supervised service interruption");
    await page
      .getByRole("listbox", { name: "Affected services", exact: true })
      .selectOption("UI-DEMO-NELLORE-UNKNOWN");
    await page
      .getByRole("listbox", { name: "Affected routes", exact: true })
      .selectOption("UI-DEMO-NELLORE-UNKNOWN");
  });
  const boot = (await (await request.get("/api/v1/app/bootstrap")).json()).data;
  expect(
    (
      await (
        await request.get(
          `/api/v1/operations/disruptions?station_id=${boot.default_station.id}&operator_id=${boot.operators[0].id}`,
        )
      ).json()
    ).data,
  ).toEqual([]);
  const identity = await request.post("/api/v1/admin/data/users", {
    headers: auth,
    data: {
      username: "ops-browser-supervisor",
      role: "STATION_SUPERVISOR",
      operator_ids: [boot.operators[0].id],
      station_ids: [boot.default_station.id],
    },
  });
  expect(identity.ok()).toBeTruthy();
  await page.getByRole("button", { name: "Lock admin", exact: true }).click();
  await page
    .getByLabel("Administrator token")
    .fill((await identity.json()).data.token);
  await page.getByRole("button", { name: "Unlock administration" }).click();
  await page
    .getByRole("combobox", { name: "Board operator", exact: true })
    .selectOption(boot.operators[0].id);
  await page
    .getByLabel("Search board", { exact: true })
    .fill("UI-DEMO-NELLORE-UNKNOWN");
  await action(page, "UI-DEMO-NELLORE-UNKNOWN", "PUBLISH_NOTICE", async () => {
    await page
      .getByRole("combobox", {
        name: "Pending request for approval",
        exact: true,
      })
      .selectOption({ index: 1 });
  });
  await page.getByRole("tab", { name: "Disruptions", exact: true }).click();
  await expect(
    page.getByText(/DEMO supervised service interruption/),
  ).toBeVisible();
});

test("dispatcher delay platform and actual departure reach passenger enquiries with full audit", async ({
  page,
  request,
}) => {
  await login(page);
  await page
    .getByLabel("Search board", { exact: true })
    .fill("UI-DEMO-NELLORE");
  await action(page, "UI-DEMO-NELLORE", "DELAYED", async () => {
    await page.getByLabel("Delay minutes", { exact: true }).fill("15");
  });
  await action(page, "UI-DEMO-NELLORE", "PLATFORM", async () => {
    await page
      .getByLabel("Confirmed platform", { exact: true })
      .selectOption("ui-dispatch-bay2");
  });
  const boot = (await (await request.get("/api/v1/app/bootstrap")).json()).data;
  const boards = (
    await (
      await request.get(
        `/api/v1/operations/board?station_id=${boot.default_station.id}&service_date=${new Date().toLocaleDateString("en-CA")}`,
      )
    ).json()
  ).data;
  const row = boards.find(
    (r: { service_id: string }) => r.service_id === "UI-DEMO-NELLORE",
  );
  const delay = await request.post("/api/v1/enquiry", {
    data: {
      intent: "BUS_DELAY",
      trip_id: row.trip_id,
      service_id: row.service_id,
      station: boot.default_station.id,
      travel_date: row.service_date,
      at: new Date().toISOString(),
    },
  });
  const delayed = (await delay.json()).results[0];
  expect(delayed.delay_minutes).toBe(15);
  expect(delayed.estimated_departure).toBeTruthy();
  expect(delayed.platform.bay).toBe("DEMO-2");
  expect(delayed.actual_departure).toBeNull();
  const before = await request.post("/api/v1/enquiry", {
    data: {
      intent: "BUS_DEPARTED_STATUS",
      trip_id: row.trip_id,
      service_id: row.service_id,
      station: boot.default_station.id,
      origin: boot.default_station.id,
      travel_date: row.service_date,
      at: new Date().toISOString(),
    },
  });
  expect((await before.json()).results).toEqual([]);
  await action(page, "UI-DEMO-NELLORE", "DEPARTED_FROM_STOP");
  const after = await request.post("/api/v1/enquiry", {
    data: {
      intent: "BUS_DEPARTED_STATUS",
      service_id: row.service_id,
      station: boot.default_station.id,
      origin: boot.default_station.id,
      travel_date: row.service_date,
      at: new Date().toISOString(),
    },
  });
  expect((await after.json()).results[0].actual_departure).toBeTruthy();
  await page.getByRole("tab", { name: "History", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Append-only event history" }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "DEPARTED_FROM_STOP · 3" }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/phase5b-dispatcher.png",
    fullPage: true,
  });
});

test("passenger board refreshes over WebSocket and reconnect refetches authoritative state", async ({
  page,
  context,
  request,
}) => {
  const boot = (await (await request.get("/api/v1/app/bootstrap")).json()).data;
  await page.goto("/board");
  await page
    .getByLabel("Search board", { exact: true })
    .fill("UI-DEMO-NELLORE-CHEAP");
  await expect(
    page.getByText("Connected locally", { exact: true }),
  ).toBeVisible();
  const service = (
    await (
      await request.get("/api/v1/admin/schedules?q=UI-DEMO-NELLORE-CHEAP", {
        headers: auth,
      })
    ).json()
  ).data.find((s: { id: string }) => s.id === "UI-DEMO-NELLORE-CHEAP");
  const day = new Date().toLocaleDateString("en-CA");
  const opened = await request.post("/api/v1/operations/trips", {
    headers: auth,
    data: {
      service_id: service.id,
      service_date: day,
      station_id: boot.default_station.id,
      source_id: "ui-expiry-source",
    },
  });
  expect(opened.ok()).toBeTruthy();
  const trip = (await opened.json()).data;
  await context.setOffline(true);
  await expect(page.getByText(/Disconnected · retrying/)).toBeVisible();
  const changed = await request.post(
    `/api/v1/operations/trips/${trip.id}/events`,
    {
      headers: auth,
      data: {
        event_type: "BOARDING",
        station_id: boot.default_station.id,
        source_id: "ui-expiry-source",
        expected_version: 0,
        idempotency_key: crypto.randomUUID(),
        occurred_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
        reason: "DEMO event while passenger client disconnected",
      },
    },
  );
  expect(changed.ok()).toBeTruthy();
  const authority = await request.get(
    `/api/v1/operations/board?station_id=${boot.default_station.id}&service_date=${day}`,
  );
  const authoritative = (await authority.json()).data.find(
    (row: { service_id: string }) => row.service_id === service.id,
  );
  expect(authoritative.phase, JSON.stringify(authoritative)).toBe("BOARDING");
  await context.setOffline(false);
  await expect(
    page.getByText("Connected locally", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("BOARDING", { exact: true })).toBeVisible();
});

test("viewer cannot mutate and cancellations appear separately on the public board", async ({
  page,
  request,
}) => {
  const boot = (await (await request.get("/api/v1/app/bootstrap")).json()).data;
  const op = boot.operators[0].id;
  const identity = await request.post("/api/v1/admin/data/users", {
    headers: auth,
    data: {
      username: "ops-browser-viewer",
      role: "OPERATIONS_VIEWER",
      operator_ids: [op],
      station_ids: [boot.default_station.id],
    },
  });
  expect(identity.status()).toBe(201);
  await page.goto("/admin/operations");
  await page
    .getByLabel("Administrator token")
    .fill((await identity.json()).data.token);
  await page.getByRole("button", { name: "Unlock administration" }).click();
  await expect(
    page.getByRole("button", { name: "Dispatch UI-DEMO-UNKNOWN", exact: true }),
  ).toBeDisabled();
  const opened = await request.post("/api/v1/operations/trips", {
    headers: auth,
    data: {
      service_id: "UI-DEMO-UNKNOWN",
      service_date: new Date().toLocaleDateString("en-CA"),
      station_id: boot.default_station.id,
      source_id: "ui-expiry-source",
    },
  });
  const trip = (await opened.json()).data;
  const cancel = await request.post(
    `/api/v1/operations/trips/${trip.id}/events`,
    {
      headers: auth,
      data: {
        event_type: "CANCELLED",
        station_id: boot.default_station.id,
        source_id: "ui-expiry-source",
        expected_version: 0,
        idempotency_key: crypto.randomUUID(),
        occurred_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString(),
        reason: "DEMO cancelled before departure",
      },
    },
  );
  expect(cancel.ok()).toBeTruthy();
  await page.goto("/board");
  await page.getByRole("tab", { name: "Cancelled", exact: true }).click();
  await expect(page.getByText("CANCELLED", { exact: true })).toBeVisible();
});
