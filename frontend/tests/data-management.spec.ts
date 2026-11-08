import { execFileSync } from "node:child_process";
import { test, expect, type Page } from "@playwright/test";
const token = "ui-test-only-token-never-for-deployment";
const auth = { Authorization: `Bearer ${token}` };
async function login(page: Page, path = "/admin/imports") {
  await page.goto(path);
  await page.getByLabel("Administrator token").fill(token);
  await page.getByRole("button", { name: "Unlock administration" }).click();
  await expect(
    page.getByRole("heading", { name: "Administration", exact: true }),
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

test("selected-stop route variant is a validated unpublished bundle", async ({
  page,
  request,
}) => {
  const service = (
    await (
      await request.get("/api/v1/admin/schedules?limit=100", { headers: auth })
    ).json()
  ).data.find((row: { number: string }) => row.number === "UI-DEMO-NELLORE");
  await login(page, "/admin/route-editor");
  await page
    .getByLabel("Existing route", { exact: true })
    .selectOption(service.route_id);
  await expect(
    page.getByLabel("Elapsed minutes stop 2", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("New variant name", { exact: true })
    .fill("UI selected variant");
  const created = page.waitForResponse(
    (response) =>
      response.url().endsWith("/admin/data/changes") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", {
      name: "Create selected-stop variant draft",
      exact: true,
    })
    .click();
  const batch = (await (await created).json()).data;
  expect(batch.workflow_state).toBe("DRAFT");
  const validated = await request.post(
    `/api/v1/admin/imports/batches/${batch.id}/validate`,
    { headers: auth, data: { revision: batch.revision } },
  );
  expect((await validated.json()).data.validation_report.errors).toEqual([]);
  expect(
    (
      await (
        await request.get(
          "/api/v1/admin/route-variants?q=UI%20selected%20variant",
          { headers: auth },
        )
      ).json()
    ).data,
  ).toEqual([]);
});

test("Import Center maps validates independently approves publishes and rolls back actual aliases", async ({
  page,
  request,
}) => {
  const bootstrap = (await (await request.get("/api/v1/app/bootstrap")).json())
    .data;
  const destination = (
    await (await request.get("/api/v1/stations/resolve?value=Tirupati")).json()
  ).data.candidates[0];
  const op = bootstrap.operators[0].id;
  await login(page);
  await page.getByLabel("Managing operator").selectOption(op);
  const center = page.getByRole("region", { name: "Staged Import Center" });
  await center.getByLabel("Import resource").selectOption("station-aliases");
  await center.getByLabel("CSV or XLSX file").setInputFiles({
    name: "DEMO-aliases.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      `station_id,name,dataset_source\n${destination.id},Phase five arrival alias,DEMO\n`,
    ),
  });
  const uploaded = page.waitForResponse((r) =>
    r.url().endsWith("/imports/files/station-aliases"),
  );
  await center
    .getByRole("button", { name: "Upload draft", exact: true })
    .click();
  const response = await uploaded;
  expect(response.status()).toBe(201);
  let batch = (await response.json()).data;
  expect(
    (
      await (
        await request.get(
          "/api/v1/stations/search?q=Phase%20five%20arrival%20alias",
        )
      ).json()
    ).data,
  ).toEqual([]);
  const validated = page.waitForResponse((r) =>
    r.url().endsWith(`/${batch.id}/validate`),
  );
  await center
    .getByRole("button", { name: "Validate change set", exact: true })
    .click();
  batch = (await (await validated).json()).data;
  expect(batch.validation_report.errors).toEqual([]);
  const provisioned = await request.post("/api/v1/admin/data/users", {
    headers: auth,
    data: {
      username: "browser-reviewer-5a",
      role: "APPROVER",
      operator_ids: [op],
    },
  });
  expect(provisioned.status()).toBe(201);
  const reviewer = (await provisioned.json()).data;
  const approved = await request.post(
    `/api/v1/admin/imports/batches/${batch.id}/approve`,
    {
      headers: { Authorization: `Bearer ${reviewer.token}` },
      data: {
        revision: batch.revision,
        reason: "Independent browser integration review",
      },
    },
  );
  expect(approved.ok()).toBe(true);
  batch = (await approved.json()).data;
  await center.getByRole("button", { name: "Refresh verification" }).click();
  await center
    .getByRole("button", { name: "Publish approved changes" })
    .click();
  const published = page.waitForResponse((r) =>
    r.url().endsWith(`/${batch.id}/publish`),
  );
  await page
    .getByRole("dialog")
    .getByRole("button", { name: /Confirm/ })
    .click();
  batch = (await (await published).json()).data;
  expect(batch.workflow_state).toBe("PUBLISHED");
  const alias = (
    await (
      await request.get(
        "/api/v1/stations/search?q=Phase%20five%20arrival%20alias",
      )
    ).json()
  ).data;
  expect(alias[0].id).toBe(destination.id);
  const interpreted = await request.post("/api/v1/conversation/message", {
    data: {
      text: "Next bus to Phase five arrival alias?",
      language: "en",
      station_context: bootstrap.default_station.id,
    },
  });
  expect((await interpreted.json()).context.destination).toBe(destination.id);
  await center.getByRole("button", { name: "Request safe rollback" }).click();
  const rolled = page.waitForResponse((r) =>
    r.url().endsWith(`/${batch.id}/rollback`),
  );
  await page
    .getByRole("dialog")
    .getByRole("button", { name: /Confirm/ })
    .click();
  expect((await (await rolled).json()).data.workflow_state).toBe("ARCHIVED");
  expect(
    (
      await (
        await request.get(
          "/api/v1/stations/search?q=Phase%20five%20arrival%20alias",
        )
      ).json()
    ).data,
  ).toEqual([]);
});

test("custom CSV columns require explicit mapping before validation", async ({
  page,
  request,
}) => {
  await login(page);
  const center = page.getByRole("region", { name: "Staged Import Center" });
  await center.getByLabel("CSV or XLSX file").setInputFiles({
    name: "DEMO-mapped.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "Station code,Station name,Origin source\nUI-5A-MAP,DEMO mapped station,DEMO\n",
    ),
  });
  await center
    .getByRole("button", { name: "Upload draft", exact: true })
    .click();
  await center
    .getByLabel("Map Station code", { exact: true })
    .selectOption("code");
  await center
    .getByLabel("Map Station name", { exact: true })
    .selectOption("name");
  await center
    .getByLabel("Map Origin source", { exact: true })
    .selectOption("dataset_source");
  await center.getByRole("button", { name: "Save column mapping" }).click();
  await center
    .getByRole("button", { name: "Validate change set", exact: true })
    .click();
  await expect(center.getByText(/1 validated row/)).toBeVisible();
  expect(
    (await (await request.get("/api/v1/stations/search?q=UI-5A-MAP")).json())
      .data,
  ).toEqual([]);
});

test("Import Center shows real row errors and blocks publication", async ({
  page,
}) => {
  await login(page);
  const center = page.getByRole("region", { name: "Staged Import Center" });
  await center.getByLabel("CSV or XLSX file").setInputFiles({
    name: "DEMO-invalid.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "code,name,dataset_source,timezone\nUI-BAD-5A,DEMO bad zone,DEMO,No/SuchZone\n",
    ),
  });
  await center
    .getByRole("button", { name: "Upload draft", exact: true })
    .click();
  await center
    .getByRole("button", { name: "Validate change set", exact: true })
    .click();
  await expect(
    center.getByRole("alert").filter({ hasText: /timezone/ }),
  ).toBeVisible();
  await expect(
    center.getByRole("button", { name: "Publish approved changes" }),
  ).toHaveCount(0);
});

test("route and timetable editors create drafts without changing current records", async ({
  page,
  request,
}) => {
  await login(page, "/admin/timetable-editor");
  const services = (
    await (
      await request.get("/api/v1/admin/schedules?limit=100", { headers: auth })
    ).json()
  ).data;
  const service = services.find((s: any) => s.id === "UI-DEMO-NELLORE");
  await page
    .getByLabel("Timetable service", { exact: true })
    .selectOption(service.id);
  await expect(
    page.getByLabel("Arrival offset stop 1", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Departure offset stop 2", { exact: true }).fill("190");
  await page
    .getByRole("button", { name: "Save timetable draft", exact: true })
    .click();
  await expect(page.getByText("Timetable saved as a draft.")).toBeVisible();
  const stored = await request.get(`/api/v1/admin/stop-times?q=${service.id}`, {
    headers: auth,
  });
  expect(
    (await stored.json()).data.filter((r: any) => r.service_id === service.id),
  ).toEqual([]);
  await page
    .getByRole("link", { name: "Route & stop editor", exact: true })
    .click();
  await page
    .getByLabel("Existing route", { exact: true })
    .selectOption(service.route_id);
  await expect(
    page.getByLabel("Elapsed minutes stop 2", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Copy as a new route" }).click();
  await page.getByLabel("Route code", { exact: true }).fill("UI-5A-COPY-ROUTE");
  await page.getByRole("button", { name: "Save route draft" }).click();
  await expect(page.getByText("Unpublished route change saved.")).toBeVisible();
  const routes = (
    await (
      await request.get("/api/v1/admin/routes?q=UI-5A-COPY-ROUTE", {
        headers: auth,
      })
    ).json()
  ).data;
  expect(routes).toEqual([]);
});

test("scoped approver UI cannot edit records and audit history is real", async ({
  page,
  request,
}) => {
  const op = (await (await request.get("/api/v1/app/bootstrap")).json()).data
    .operators[0].id;
  const p = await request.post("/api/v1/admin/data/users", {
    headers: auth,
    data: {
      username: "browser-readonly-5a",
      role: "APPROVER",
      operator_ids: [op],
    },
  });
  const reviewer = (await p.json()).data;
  await page.goto("/admin/stations");
  await page.getByLabel("Administrator token").fill(reviewer.token);
  await page.getByRole("button", { name: "Unlock administration" }).click();
  await expect(page.getByRole("button", { name: "Add record" })).toHaveCount(0);
  await page.getByRole("link", { name: "Audit History", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Audit history", exact: true }),
  ).toBeVisible();
  expect(
    (
      await request.post("/api/v1/admin/data/users", {
        headers: { Authorization: `Bearer ${reviewer.token}` },
        data: { username: "not-allowed", role: "EDITOR", operator_ids: [op] },
      })
    ).status(),
  ).toBe(403);
});

test("XLSX file is parsed locally and the template download uses the real schema", async ({
  page,
}) => {
  await login(page);
  const center = page.getByRole("region", { name: "Staged Import Center" });
  const content = execFileSync("python", [
    "-c",
    "import openpyxl,io,sys; b=openpyxl.Workbook(); s=b.active; s.append(['code','name','dataset_source']); s.append(['UI-5A-XLSX','DEMO workbook station','DEMO']); f=io.BytesIO(); b.save(f); sys.stdout.buffer.write(f.getvalue())",
  ]);
  await center.getByLabel("CSV or XLSX file").setInputFiles({
    name: "DEMO-stations.xlsx",
    mimeType:
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: content,
  });
  await center
    .getByRole("button", { name: "Upload draft", exact: true })
    .click();
  await center
    .getByRole("button", { name: "Validate change set", exact: true })
    .click();
  await expect(center.getByText(/1 validated row/)).toBeVisible();
  const downloaded = page.waitForEvent("download");
  await center.getByRole("button", { name: "Download CSV template" }).click();
  const file = await downloaded;
  expect(file.suggestedFilename()).toBe("FICTIONAL-template-stations.csv");
});

test("strict production CRUD creates a draft and requires independent publication", async ({
  page,
  request,
}) => {
  const root = "http://127.0.0.1:8021";
  await login(page, root + "/admin/stations");
  await page.getByRole("button", { name: "Add record", exact: true }).click();
  const form = page.getByRole("dialog");
  await form.getByLabel("dataset source", { exact: true }).fill("DEMO");
  await form.getByLabel("code", { exact: true }).fill("UI-5A-STRICT");
  await form
    .getByLabel("name", { exact: true })
    .fill("DEMO unpublished station");
  const staged = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/admin/stations") &&
      r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Save record" }).click();
  const response = await staged;
  expect(response.status()).toBe(201);
  let batch = (await response.json()).data;
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByText(/Draft saved. Passenger data is unchanged/),
  ).toBeVisible();
  expect(
    (
      await (
        await request.get(root + "/api/v1/stations/search?q=UI-5A-STRICT")
      ).json()
    ).data,
  ).toEqual([]);
  const reviewerResponse = await request.post(
    root + "/api/v1/admin/data/users",
    {
      headers: auth,
      data: {
        username: "strict-global-reviewer",
        role: "APPROVER",
        global_scope: true,
      },
    },
  );
  expect(reviewerResponse.status()).toBe(201);
  const reviewer = (await reviewerResponse.json()).data;
  const validated = await request.post(
    root + `/api/v1/admin/imports/batches/${batch.id}/validate`,
    { headers: auth, data: { revision: batch.revision } },
  );
  expect(validated.ok()).toBe(true);
  batch = (await validated.json()).data;
  expect(batch.validation_report.errors).toEqual([]);
  const approved = await request.post(
    root + `/api/v1/admin/imports/batches/${batch.id}/approve`,
    {
      headers: { Authorization: `Bearer ${reviewer.token}` },
      data: { revision: batch.revision },
    },
  );
  expect(approved.ok()).toBe(true);
  batch = (await approved.json()).data;
  const published = await request.post(
    root + `/api/v1/admin/imports/batches/${batch.id}/publish`,
    { headers: auth, data: { revision: batch.revision } },
  );
  expect(published.ok()).toBe(true);
  expect(
    (
      await (
        await request.get(root + "/api/v1/stations/search?q=UI-5A-STRICT")
      ).json()
    ).data[0].code,
  ).toBe("UI-5A-STRICT");
});
